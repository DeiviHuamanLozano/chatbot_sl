LOCATION=us
PROJECT_ID=py-social-listening
ARTIFACT_REGISTRY_REPOSITORY=sl-chat
IMAGE_NAME=twilio-webhook
TAG=latest

container_up:
	sudo chmod 777 /var/run/docker.sock
	docker build -t $(IMAGE_NAME) .
	docker run --env-file ./.env -p 8001:8001 -v .:/app $(IMAGE_NAME)
container_it:
	sudo chmod 777 /var/run/docker.sock
	docker build -t $(IMAGE_NAME) .
	docker run -it --env-file ./.env -p 8001:8001 -v .:/app $(IMAGE_NAME) /bin/bash
container_enter:
	sudo chmod 777 /var/run/docker.sock
	docker exec -it $(shell docker ps -q -l -n 1) /bin/bash
check_repo:
	gcloud artifacts repositories describe $(ARTIFACT_REGISTRY_REPOSITORY) --project=$(PROJECT_ID) --location=$(LOCATION)
deploy_to_ar:
	sudo chmod 777 /var/run/docker.sock
	docker build -t $(IMAGE_NAME) .
	gcloud auth login
#	gcloud auth application-default login
	gcloud auth configure-docker $(LOCATION)-docker.pkg.dev
# gcloud auth configure-docker us-west1-docker.pkg.dev
# gcloud auth configure-docker us-east1-docker.pkg.dev
	docker tag $(IMAGE_NAME) $(LOCATION)-docker.pkg.dev/$(PROJECT_ID)/$(ARTIFACT_REGISTRY_REPOSITORY)/$(IMAGE_NAME):$(TAG)
	docker push $(LOCATION)-docker.pkg.dev/$(PROJECT_ID)/$(ARTIFACT_REGISTRY_REPOSITORY)/$(IMAGE_NAME):$(TAG)
check_deploy:
	gcloud artifacts docker images list $(LOCATION)-docker.pkg.dev/$(PROJECT_ID)/$(ARTIFACT_REGISTRY_REPOSITORY)/$(IMAGE_NAME) --include-tags
# https://cloud.google.com/artifact-registry/docs/docker/pushing-and-pulling?hl=es-419
ngrok_upserver:
	ngrok http http://localhost:8001
