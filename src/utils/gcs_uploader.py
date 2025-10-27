"""
Helper para upload de imagens no Google Cloud Storage.
"""

import io
import logging
from datetime import datetime
from uuid import uuid4

from google.cloud import storage
from google.oauth2 import service_account

from src.config import config

logger = logging.getLogger(__name__)


class GCSUploader:
    """Gerenciador de upload para Google Cloud Storage."""

    def __init__(self):
        """Inicializa cliente GCS."""
        # Prioridade: JSON_CONTENT (string) > JSON (path) > ADC

        if config.gcs.service_account_json_content:
            # Opção 1: JSON como string na variável de ambiente
            import json
            credentials_info = json.loads(config.gcs.service_account_json_content)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info
            )
            self.client = storage.Client(
                credentials=credentials, project=config.gcs.project_id
            )
        elif config.gcs.service_account_json:
            # Opção 2: Path para arquivo JSON
            credentials = service_account.Credentials.from_service_account_file(
                config.gcs.service_account_json
            )
            self.client = storage.Client(
                credentials=credentials, project=config.gcs.project_id
            )
        else:
            # Opção 3: Application Default Credentials
            self.client = storage.Client(project=config.gcs.project_id)

        self.bucket = self.client.bucket(config.gcs.bucket_name)

    def upload_image(
        self,
        image_buffer: io.BytesIO,
        content_type: str = "image/png",
        filename: str | None = None,
        public: bool = True,
    ) -> str:
        """
        Faz upload de imagem e retorna URL pública.

        Args:
            image_buffer: Buffer com imagem
            content_type: MIME type
            filename: Nome do arquivo (gera UUID se None)
            public: Se deve ser publicamente acessível

        Returns:
            URL pública da imagem
        """
        try:
            # Gerar filename único
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"charts/{timestamp}_{uuid4().hex[:8]}.png"

            # Upload
            blob = self.bucket.blob(filename)
            blob.upload_from_file(
                image_buffer, content_type=content_type, rewind=True
            )

            # Com uniform bucket-level access, não podemos usar make_public()
            # A URL pública funciona se o bucket tiver permissão allUsers:objectViewer
            # Retornar URL pública
            url = blob.public_url
            logger.info(f"Imagem uploaded: {url}")
            return url

        except Exception as e:
            logger.error(f"Erro ao fazer upload: {e}", exc_info=True)
            raise


# Singleton
gcs_uploader = GCSUploader()
