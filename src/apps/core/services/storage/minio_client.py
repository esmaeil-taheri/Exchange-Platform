from minio import Minio
from django.conf import settings
from datetime import timedelta


class MinioClient:
    def __init__(self, bucket_name: str):
        self.client = Minio(
            settings.OBJECT_STORAGE_ENDPOINT_URL,
            access_key=settings.OBJECT_STORAGE_ACCESS_KEY,
            secret_key=settings.OBJECT_STORAGE_SECRET_KEY,
            secure=settings.OBJECT_STORAGE_SECURE,
        )
        self.bucket = bucket_name

        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_file(self, file_obj, object_name, content_type):
        """
        Upload a file-like object to MinIO.
        """
        self.client.put_object(
            bucket_name=self.bucket,
            object_name=object_name,
            data=file_obj,
            length=file_obj.size,
            content_type=content_type
        )

        return object_name  # path

    def generate_url(self, object_name):
        """
        Create a temporary download URL
        """
        return self.client.presigned_get_object(
            bucket_name=self.bucket,
            object_name=object_name,
        )

    def delete_file(self, object_name):
        self.client.remove_object(
            bucket_name=self.bucket,
            object_name=object_name
        )
