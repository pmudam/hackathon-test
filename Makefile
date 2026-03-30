PYTHONPATH ?= src
TF_DIR ?= infra/terraform
ENV_FILE ?= .env

.PHONY: test run run-json tf-init tf-fmt tf-validate tf-plan tf-apply tf-destroy live-rca continuous-rca all-auto schedule-rca

test:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s tests -v

run:
	PYTHONPATH=$(PYTHONPATH) python3 -m rca_assistant.cli

run-json:
	PYTHONPATH=$(PYTHONPATH) python3 -m rca_assistant.cli --json

tf-init:
	cd $(TF_DIR) && terraform init

tf-fmt:
	cd $(TF_DIR) && terraform fmt

tf-validate:
	cd $(TF_DIR) && terraform validate

tf-plan:
	@if [ -f $(ENV_FILE) ]; then set -a; . ./$(ENV_FILE); set +a; fi; \
	export TF_VAR_splunk_api_url="$$SPLUNK_API_URL"; \
	export TF_VAR_splunk_auth_token="$${SPLUNK_AUTH_TOKEN:-$$SPLUNK_API_TOKEN}"; \
	cd $(TF_DIR) && terraform plan

tf-apply:
	@if [ -f $(ENV_FILE) ]; then set -a; . ./$(ENV_FILE); set +a; fi; \
	export TF_VAR_splunk_api_url="$$SPLUNK_API_URL"; \
	export TF_VAR_splunk_auth_token="$${SPLUNK_AUTH_TOKEN:-$$SPLUNK_API_TOKEN}"; \
	cd $(TF_DIR) && terraform apply -auto-approve

tf-destroy:
	@if [ -f $(ENV_FILE) ]; then set -a; . ./$(ENV_FILE); set +a; fi; \
	export TF_VAR_splunk_api_url="$$SPLUNK_API_URL"; \
	export TF_VAR_splunk_auth_token="$${SPLUNK_AUTH_TOKEN:-$$SPLUNK_API_TOKEN}"; \
	cd $(TF_DIR) && terraform destroy -auto-approve

live-rca:
	@if [ -f $(ENV_FILE) ]; then set -a; . ./$(ENV_FILE); set +a; fi; \
	if [ -z "$$SPLUNK_DETECTOR_ID" ] || [ "$$SPLUNK_DETECTOR_ID" = "your_detector_id" ]; then \
		SPLUNK_DETECTOR_ID="$$(cd $(TF_DIR) && TF_LOG_PATH=/dev/null terraform output -raw splunk_detector_id 2>/dev/null || echo '')"; \
		if [ -z "$$SPLUNK_DETECTOR_ID" ]; then echo "ERROR: No detector ID found. Run 'make tf-apply' first to provision the detector."; exit 1; fi; \
		export SPLUNK_DETECTOR_ID; \
	fi; \
	export SPLUNK_AUTH_TOKEN="$${SPLUNK_AUTH_TOKEN:-$$SPLUNK_API_TOKEN}"; \
	PYTHONPATH=$(PYTHONPATH) python3 -m rca_assistant.cli --fetch-live --skip-dashboard-input

continuous-rca:
	@if [ -f $(ENV_FILE) ]; then set -a; . ./$(ENV_FILE); set +a; fi; \
	if [ -z "$$SPLUNK_DETECTOR_ID" ] || [ "$$SPLUNK_DETECTOR_ID" = "your_detector_id" ]; then \
		SPLUNK_DETECTOR_ID="$$(cd $(TF_DIR) && TF_LOG_PATH=/dev/null terraform output -raw splunk_detector_id 2>/dev/null || echo '')"; \
		if [ -z "$$SPLUNK_DETECTOR_ID" ]; then echo "ERROR: No detector ID found. Run 'make tf-apply' first to provision the detector."; exit 1; fi; \
		export SPLUNK_DETECTOR_ID; \
	fi; \
	export SPLUNK_AUTH_TOKEN="$${SPLUNK_AUTH_TOKEN:-$$SPLUNK_API_TOKEN}"; \
	PYTHONPATH=$(PYTHONPATH) python3 -m rca_assistant.continuous_rca

all-auto:
	$(MAKE) tf-apply
	$(MAKE) continuous-rca

schedule-rca:
	@echo "# Run continuously in the foreground:"
	@echo "cd $(shell pwd) && make all-auto"
	@echo "# Or cron a single RCA snapshot every hour:"
	@echo "0 * * * * cd $(shell pwd) && set -a && . ./.env && set +a && export SPLUNK_AUTH_TOKEN=\$$\${SPLUNK_AUTH_TOKEN:-\$$SPLUNK_API_TOKEN} && export SPLUNK_DETECTOR_ID=\$$(cd $(TF_DIR) && terraform output -raw splunk_detector_id) && PYTHONPATH=src python3 -m rca_assistant.cli --fetch-live --skip-dashboard-input --json >> rca_cron.log 2>&1"
