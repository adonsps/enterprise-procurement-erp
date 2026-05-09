FROM odoo:17.0

USER root

# Install system dependencies for OCR and data processing
RUN apt-get update && apt-get install -y \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python libraries for AI, NLP, and Data Analytics
RUN pip3 install \
    pandas \
    openai \
    cryptography \
    pytesseract

USER odoo