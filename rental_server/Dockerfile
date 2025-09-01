FROM eclipse-temurin:17-jdk-alpine

WORKDIR /minecraft

RUN apk add --no-cache curl

# PaperMC 1.20.1のビルド103をダウンロード
RUN curl -o server.jar -L https://api.papermc.io/v2/projects/paper/versions/1.20.1/builds/103/downloads/paper-1.20.1-103.jar

RUN echo "eula=true" > eula.txt

CMD ["java", "-Xms1G", "-Xmx2G", "-jar", "server.jar", "nogui"]

