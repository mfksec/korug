FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for DNS queries and tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    unzip \
    nmap \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Subfinder
RUN curl -fsSL --retry 3 --retry-delay 2 https://github.com/projectdiscovery/subfinder/releases/download/v2.14.0/subfinder_2.14.0_linux_amd64.zip -o subfinder.zip && \
    unzip subfinder.zip && \
    mv subfinder /usr/local/bin/ && \
    chmod +x /usr/local/bin/subfinder && \
    rm subfinder.zip

# Install Amass
RUN curl -fsSL --retry 3 --retry-delay 2 https://github.com/owasp-amass/amass/releases/download/v5.1.1/amass_linux_amd64.tar.gz -o amass.tar.gz && \
    tar -xzf amass.tar.gz && \
    mv amass_linux_amd64/amass /usr/local/bin/ && \
    chmod +x /usr/local/bin/amass && \
    rm -rf amass.tar.gz amass_linux_amd64

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ /app/src/

# Set Python path
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Create a non-root user
RUN useradd -m -u 1000 korug && \
    chown -R korug:korug /app

USER korug

EXPOSE 8000

CMD ["python", "-m", "korug.run"]
