from django.urls import path
from .views import FileListView, upload_file, delete_file, download_file

app_name = 'files'

urlpatterns = [
    path('', FileListView.as_view(), name='file_list'),
    path('upload/', upload_file, name='upload_file'),
    path('delete/<int:file_id>/', delete_file, name='delete_file'),
    path('download/<int:file_id>/', download_file, name='download_file'),
]