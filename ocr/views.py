import glob
import multiprocessing
import os
from datetime import datetime
from difflib import get_close_matches

import cv2
import easyocr
import imutils
import matplotlib.pyplot as plt
import numpy
import pandas as pd
import torch
import xlwt
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse
from django.shortcuts import render
from pdf2image import convert_from_path
from PIL import Image
from xlrd import open_workbook
from xlutils.copy import copy

current_time = datetime.now()

def vertical_crop(image_row):
  block_images = []
  
  for image in image_row:
    left = 0
    right = 753
    for i in range (3):
      cropped = image.crop((left, 0, right, 300))
      left = left + 753
      right = right + 753
      block_images.append(cropped)

  return block_images


def horizontal_crop(image,topPoint,bottomPoint):
  cropped_main_container = image.crop((69,topPoint,1575,bottomPoint))
 
  clear_image = make_image_clear(cropped_main_container,width=2259,height=2984)

  image_row = []
  top = 0
  bottom = 299
  for i in range(10):
    cropped = clear_image.crop((0,top,2259,bottom))
    top = top + 299
    bottom = bottom + 299
    image_row.append(cropped)

  block_images = vertical_crop(image_row)
  return block_images


def make_image_clear(image,width,height):

    zoom_image = image.resize((width,height), Image.LANCZOS)
    
    open_cv_image = numpy.array(zoom_image) 
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    dilated_img = cv2.dilate(gray, numpy.ones((7, 7), numpy.uint8))
    bg_img = cv2.medianBlur(dilated_img, 21)
    diff_img = 255 - cv2.absdiff(gray, bg_img)
    norm_img = cv2.normalize(diff_img, None, alpha=0, beta=255,norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
    work_img = cv2.threshold(norm_img, 0, 255, cv2.THRESH_OTSU)[1]

    pil_image = Image.fromarray(work_img)

    # pil_image.save("pil.jpg")
    return pil_image


def createCsv (filename):
    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet(filename)
    file_path = (f'{(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}')
    workbook.save(f'{file_path}/output/{filename}.xls')
    return 
  

def insertDataToCSV(block_data,filename):
  row_data = []
  file_path = (f'{(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}')
  rb = open_workbook(f'{file_path}/output/{filename}.xls')
  wb = copy(rb)

  s = wb.get_sheet(0)

  xlwt.add_palette_colour("custom_colour", 0x21)
  wb.set_colour_RGB(0x21, 251, 228, 228)

  style = xlwt.easyxf('pattern: pattern solid, fore_colour custom_colour; font: bold on, height 250;; borders: bottom dashed')

  columns = ['seq_no', 'card_no', 'name', 'father_husband_name', 'address','age', 'gender', 'yadi_no', 'election_address']
  
  for count,column in enumerate(columns):
      s.write(0, count, column,style)

  for i in range(9):
    s.col(i+1).width = int(27 * 260)

  row_length = len(s._Worksheet__rows)

  total_length = len(block_data)

  previous_row_name = ''

  title_word = ["Name", "Husband's Name", "Father's Name", "House Number", "Age", "Gender", "Age :", "Gender :"]

  for column,data in enumerate(block_data):
    # print(previous_row_name,column,data)
    title = get_close_matches(data,title_word)

    if len(title) >0:
        previous_row_name = data
        continue

    elif column == total_length - 2 :
      s.write(row_length,7,data)
    
    elif column == total_length - 1 :
      s.write(row_length,8,data)

    elif column == 0 and len(data) <=9: 
        s.write(row_length,0,data)
    
    elif column == 0 and len(data) == 10: 
        s.write(row_length,1,data)
     
    elif column == 1 and len(data) == 10: 
        s.write(row_length,1,data)
    
    elif get_close_matches(previous_row_name,["name"])  :
       s.write(row_length,2,data)

    elif get_close_matches(previous_row_name,["Husband's Name","Father's Name"]): 
      s.write(row_length,3,data)

    elif get_close_matches(previous_row_name,['House Number']) :
      s.write(row_length,4,data)

    elif get_close_matches(previous_row_name,['Age', 'Age :']) :
      s.write(row_length,5,data)
    
    elif get_close_matches(previous_row_name,['Gender', 'Gender :']) :
      s.write(row_length,6,data)
    
    else:
       continue

  wb.save(f'{file_path}/output/{filename}.xls')


def ocr(image,topPoint,bottomPoint,first_page_info,filename):
  block_images = horizontal_crop(image,topPoint,bottomPoint)
  reader = easyocr.Reader(['en'],verbose=False)
  ignore_word_list = ['Available' ,'Photo is','Photo','is']
  for image in block_images:
      open_cv_image = numpy.array(image) 
      result = reader.readtext(open_cv_image,detail= 0, paragraph=False,width_ths=0.4)
      final_result = [element for element in result if element not in ignore_word_list]
      final_result.extend(first_page_info)
      insertDataToCSV(final_result,filename)
      # print(final_result)
      # print(f'Fecthing : {filename}.....')
      
      
def cropFirstPage(image):
    total_crop_blocks = []
    first_page_info = []
    part_number_crop = image.crop((75,115,1500,200))
    address_crop = image.crop((75,1500,880,1630))

    total_crop_blocks.extend([part_number_crop,address_crop])

    reader = easyocr.Reader(['en'], verbose=False)

    ignore_word_list = ['4.', 'NUMBER', 'OF', 'ELECTORS','Address', 'of Polling Station', ':','No. Name and Reservation Status of Assembly Constituency : 212','No. Name and Reservation Status of Assembly Constituency :212', 'Parvati ', 'Part number', 'IIGEN)']
    
    for crop_block in total_crop_blocks:
      clear_image = make_image_clear(crop_block,width=2850,height=340)
      open_cv_image = numpy.array(clear_image) 
      result = reader.readtext(open_cv_image,detail= 0, paragraph=False,width_ths=0.4)
      final_result = [element for element in result if element not in ignore_word_list]

      join_result = ' '.join(final_result)
      first_page_info.append(join_result)
  
    return first_page_info


def cleanMedia():
  media_files = glob.glob(f'{(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}/media/*')
  
  for f in media_files:
    os.remove(f)
    
  return

def cleanOutput():
  output_files = glob.glob(f'{(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}/output/*')

  for f in output_files:
    os.remove(f)
    
  return

def clearLogFile():
  log_file_path = f'{(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}/log.txt'
  
  with open(log_file_path, "w") as file:
      file.truncate(0)
      
  return

def exclude_hidden_files(file_list):
    return [f for f in file_list if not f.startswith('.')]
  
def fetchFiles():
  log_file_path = f'{(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}/log.txt'
  path =f'{(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}/media/'
  
  directory_contents = os.listdir(path)
  files = exclude_hidden_files(directory_contents)
  
  fs = FileSystemStorage()
  
  for idx,file in enumerate(files) :
    file_name = file
       
    print(f'Total Fetching Completed {idx + 1}/{len(files)}')
    print(f'Now Fetching Data from {file}.......')
    
    uploaded_file_url = fs.url(file)
          
    file_path = (f'{(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}{uploaded_file_url}')
    images = convert_from_path(file_path)

    createCsv(file)
    
    for idx, image in enumerate(images):
        if idx == 0:
          first_page_info = cropFirstPage(image=image)
        if idx == 2:
          ocr(image=image,topPoint=138,bottomPoint=2127, first_page_info=first_page_info,filename=file)
        if idx > 2:
          ocr(image=image,topPoint=114,bottomPoint=2103,first_page_info=first_page_info,filename=file)
    
    current_time_str = current_time.strftime('%d-%m-%Y %H:%M:%S')
    
    with open(log_file_path, 'a') as file:
      file.write(f'{current_time_str} - {file_name}\n')  
          
    print(f'{file} -- Fetched Completed')
  
  current_time_str = current_time.strftime('%d-%m-%Y %H:%M:%S')
  with open(log_file_path, 'a') as file:
      file.write(f"{current_time_str}  Fetched All Data From All Files \n")  
  print("Fetched Completed")
  file.close()
  return
 
def UploadView(request):
    if "uploadFile" in request.POST and "myfile" in request.FILES:
        media_files = glob.glob(f'{(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}/media/*')
        log_file_path = f'{(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}/log.txt'
        
        files = request.FILES.getlist('myfile')
        
        fs = FileSystemStorage()
        
        for idx,file in enumerate(files):
          print(f'uploading file to media {idx+1}/{len(files)} [{file.name}]')
          file_name = file.name.replace(' ', '_')
          filename = fs.save(file_name,file)
        
        current_time_str = current_time.strftime('%d-%m-%Y %H:%M:%S')
        
        with open(log_file_path, 'a') as file:
            file.write(f'{current_time_str} - All files uploaded successfully \n')  
        file.close() 
                
        print(f'All files uploaded successfully')
        
    else:
      print("Please Upload files.")

    if 'clearMedia' in request.POST:
      cleanMedia()

    if 'clearOutput' in request.POST:
      cleanOutput()
    
    if 'fetchFile' in request.POST:
      fetchFiles()
    
    if 'clearLogFile' in request.POST:
      clearLogFile() 
        
    return render(request, 'ocr/upload_form.html')