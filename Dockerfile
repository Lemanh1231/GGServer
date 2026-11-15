FROM eclipse-temurin:21-jdk AS build
WORKDIR /app
COPY . .
RUN chmod +x gradlew && ./gradlew --no-daemon test fatJar

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /app/build/libs/ggserver-1.0.0-all.jar ./ggserver.jar
COPY --from=build /app/resources ./resources
COPY --from=build /app/resources/docker/server-config.json ./resources/server-config.json
RUN mkdir -p resources/data resources/captures && chown -R 10001:10001 /app
USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/ggserver.jar"]
