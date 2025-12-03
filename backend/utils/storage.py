"""
Storage Client for Supabase Storage Operations.

Purpose:
    Provides a unified interface for uploading, retrieving, and deleting files
    from Supabase Storage buckets. Used for storing certificates and exports.

Usage:
    from utils.storage import StorageClient
    
    storage = StorageClient()
    url = await storage.upload_file(
        bucket='certificates',
        file_name='cert_123.pdf',
        file_data=pdf_bytes,
        content_type='application/pdf'
    )
"""
from typing import Optional
from supabase import create_client, Client
from config import settings
import logging

logger = logging.getLogger(__name__)


class StorageClient:
    """Client for interacting with Supabase Storage."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
        self.storage = self.client.storage
    
    async def upload_file(
        self,
        bucket: str,
        file_name: str,
        file_data: bytes,
        content_type: str = 'application/octet-stream',
        upsert: bool = False
    ) -> str:
        """
        Upload a file to Supabase Storage.
        
        Args:
            bucket: The storage bucket name (e.g., 'certificates', 'exports')
            file_name: The name/path for the file in the bucket
            file_data: The file content as bytes
            content_type: MIME type of the file
            upsert: If True, overwrite existing file with same name
            
        Returns:
            str: The public URL of the uploaded file
            
        Raises:
            Exception: If upload fails
            
        Example:
            url = await storage.upload_file(
                bucket='certificates',
                file_name='cert_abc123.pdf',
                file_data=pdf_bytes,
                content_type='application/pdf'
            )
        """
        try:
            # Upload file to bucket
            response = self.storage.from_(bucket).upload(
                path=file_name,
                file=file_data,
                file_options={
                    "content-type": content_type,
                    "upsert": str(upsert).lower()
                }
            )
            
            # Get the public URL for the uploaded file
            public_url = self.get_public_url(bucket, file_name)
            
            logger.info(f"Successfully uploaded file to {bucket}/{file_name}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload file to {bucket}/{file_name}: {str(e)}")
            raise Exception(f"Storage upload failed: {str(e)}")
    
    def get_public_url(self, bucket: str, file_name: str) -> str:
        """
        Get the public URL for a file in storage.
        
        Args:
            bucket: The storage bucket name
            file_name: The name/path of the file in the bucket
            
        Returns:
            str: The public URL to access the file
            
        Example:
            url = storage.get_public_url('certificates', 'cert_abc123.pdf')
            # Returns: https://xxx.supabase.co/storage/v1/object/public/certificates/cert_abc123.pdf
        """
        try:
            public_url = self.storage.from_(bucket).get_public_url(file_name)
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to get public URL for {bucket}/{file_name}: {str(e)}")
            raise Exception(f"Failed to get public URL: {str(e)}")
    
    async def delete_file(self, bucket: str, file_name: str) -> bool:
        """
        Delete a file from Supabase Storage.
        
        Args:
            bucket: The storage bucket name
            file_name: The name/path of the file to delete
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            Exception: If deletion fails
            
        Example:
            success = await storage.delete_file('certificates', 'cert_abc123.pdf')
        """
        try:
            response = self.storage.from_(bucket).remove([file_name])
            
            logger.info(f"Successfully deleted file from {bucket}/{file_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file from {bucket}/{file_name}: {str(e)}")
            raise Exception(f"Storage deletion failed: {str(e)}")
    
    async def list_files(
        self,
        bucket: str,
        path: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """
        List files in a storage bucket.
        
        Args:
            bucket: The storage bucket name
            path: Optional path prefix to filter files
            limit: Maximum number of files to return
            offset: Number of files to skip
            
        Returns:
            list: List of file objects with metadata
            
        Example:
            files = await storage.list_files('certificates', path='2024/')
        """
        try:
            response = self.storage.from_(bucket).list(
                path=path,
                options={
                    "limit": limit,
                    "offset": offset
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to list files in {bucket}/{path}: {str(e)}")
            raise Exception(f"Storage list failed: {str(e)}")
    
    def get_signed_url(
        self,
        bucket: str,
        file_name: str,
        expires_in: int = 3600
    ) -> str:
        """
        Generate a signed URL for temporary access to a private file.
        
        Args:
            bucket: The storage bucket name
            file_name: The name/path of the file
            expires_in: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            str: The signed URL with expiration
            
        Example:
            # Generate URL that expires in 24 hours
            url = storage.get_signed_url('exports', 'export_123.zip', expires_in=86400)
        """
        try:
            response = self.storage.from_(bucket).create_signed_url(
                path=file_name,
                expires_in=expires_in
            )
            
            if response and 'signedURL' in response:
                return response['signedURL']
            else:
                raise Exception("Failed to generate signed URL")
                
        except Exception as e:
            logger.error(f"Failed to create signed URL for {bucket}/{file_name}: {str(e)}")
            raise Exception(f"Signed URL generation failed: {str(e)}")
