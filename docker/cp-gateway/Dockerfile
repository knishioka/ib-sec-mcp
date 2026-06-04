FROM eclipse-temurin:21

WORKDIR /app

RUN apt-get update && apt-get install -y unzip curl && rm -rf /var/lib/apt/lists/*

# Download Client Portal Gateway
RUN mkdir api_gateway && cd api_gateway && \
    curl -O https://download2.interactivebrokers.com/portal/clientportal.gw.zip && \
    unzip clientportal.gw.zip && rm clientportal.gw.zip

COPY conf.yaml api_gateway/root/conf.yaml
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

EXPOSE 5000

CMD ["/app/run.sh"]
