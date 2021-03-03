# SCIM UMA Mode

An example on how to use SCIM API using UMA protection mode.

## Pre-requisites

1.  Deploy Gluu Server v4.2.
1.  Make sure SCIM container is deployed.
1.  Activate SCIM support at `/identity/organization/updateOrganization.htm`.
1.  Enable `scim_access_policy` custom scripts at `/identity/script/manageOtherScript.htm` (UMA RPT Policies tab).
1.  Obtain the following files from SCIM container:

    - `scim-rp.jks`
    - `scim-rp-keys.json`

    Save them under directory where `scim_uma.py` is located.

1.  Get `scim_rp_client_jks_pass` secret from Vault/k8s secret backend, save it into `scim_rp_jks_pass` file.
1.  Get `scim_rp_client_id` config from Consul/k8s config backend, save it into `client_id` file.

## Usage

1.  Install required libraries:

    ```python
    pip3 install -r requirements.txt --no-cache-dir
    ```

2.  Run the script (assuming base url is `https://demoexample.gluu.org`):

    ```python
    GLUU_BASE_URL=https://demoexample.gluu.org python3 scim_uma.py
    ```
