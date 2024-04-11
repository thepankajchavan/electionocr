from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
# from uploader import views as uploader_views
from ocr import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', views.UploadView, name='fileupload'),
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)