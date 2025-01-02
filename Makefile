VERSION=0.1.3

# enable or call 	NOCACHE=--no-cache make image
# NOCACHE=--no-cache

it: help

help:
	@echo Makefile zum Erzeugen eines Empfangsservice für Ande.Nachrtichten von Duplicacy.
	@echo Standardaufruf: make clean image service
	@echo Die Targets im einzelnen:
	@echo 	make clean: Lösche eventuell vorhandenen Container
	@echo 	make image: Erzeuge das Docker-image
	@echo 	make service: Erzeuge den Service auf Basis des Containers
	@echo 	make deinstall: Löschen von Container, Image und Logfile

clean:
	-docker rm -f backup-report

image:
	docker build $(NOCACHE) -t backup-report:$(VERSION) -t backup-report:latest .

service:
	docker run \
	-d \
	--restart unless-stopped \
	--name backup-report \
	--publish 5000:5000 \
	-v ./logdir:/app/logdir \
	backup-report:latest
