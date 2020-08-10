import json
import os
import shlex
import subprocess
import sys
# import time
import uuid
from datetime import datetime
from datetime import timedelta

import pem
import requests
from jwt import encode as jwt_encode

import urllib3
urllib3.disable_warnings()


def exec_cmd(cmd):
    args = shlex.split(cmd)
    popen = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = popen.communicate()
    retcode = popen.returncode
    return stdout.strip(), stderr.strip(), retcode


def get_kid(alg="RS256", jwks="scim-rp-keys.json"):
    kid = ""

    with open(jwks) as f:
        jwks = json.loads(f.read())

    for jwk in jwks.get("keys", []):
        if jwk["alg"] != alg:
            continue
        kid = jwk["kid"]
    return kid


def jks_to_pkcs12(jks, pkcs12, alias, password):
    if os.path.isfile(pkcs12):
        os.unlink(pkcs12)

    cmd = "keytool -importkeystore " \
          "-srckeystore {jks} " \
          "-srcstorepass {password} " \
          "-srckeypass {password} " \
          "-srcalias {alias} " \
          "-destalias {alias} " \
          "-destkeystore {pkcs12} " \
          "-deststoretype PKCS12 " \
          "-deststorepass {password} " \
          "-destkeypass {password}".format(jks=jks, pkcs12=pkcs12, password=password, alias=alias)
    out, err, code = exec_cmd(cmd)
    if code != 0:
        err = err or out
        print(err)
        sys.exit(code)


def certkey_from_pkcs12(src, dest, keypass):
    pubcert = ""
    privkey = ""

    cmd = "openssl pkcs12 -in {0} -nodes -out {1} -passin pass:{2}".format(src, dest, keypass)
    out, err, code = exec_cmd(cmd)
    if code != 0:
        err = err or out
        print(err)
        sys.exit(code)

    for parsed in pem.parse_file(dest):
        item = parsed.as_text()
        if item.startswith("-----BEGIN CERTIFICATE-----"):
            pubcert = item
        elif item.startswith("-----BEGIN PRIVATE KEY-----"):
            privkey = item
    return pubcert.strip(), privkey.strip()


def generate_jwt(kid, privkey, client_id, alg="RS256"):
    aud = f"{get_base_url()}/oxauth/restv1/token"
    now = datetime.utcnow()
    expire = timedelta(days=2) + now

    headers = {
        "typ": "JWT",
        "alg": alg,
        "kid": kid,
    }
    payload = {
        # This is my client ID
        "iss": client_id,
        # This is also my client ID
        "sub": client_id,
        # This is the time which this JWT will be expired. You can get epoch time from an epoch time from https://www.epochconverter.com
        "exp": expire,
        # This is the time which this jwt is created. Again use an approximate value. This can be any value in history
        "iat": now,
        # This has to be unique in every JWT you send out in a request. You can't repeat this value.
        "jti": str(uuid.uuid4()),
        "aud": aud,
    }
    return jwt_encode(payload, privkey, algorithm=alg, headers=headers)


def get_users(token=""):
    req = requests.get(
        f"{get_base_url()}/identity/restv1/scim/v2/Users",
        headers={
            "Authorization": "Bearer {}".format(token),
        },
        verify=False,
    )
    return req


def get_token(client_id, jwt, ticket=""):
    url = f"{get_base_url()}/oxauth/restv1/token"
    req = requests.post(
        url,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
            "ticket": ticket,
            "client_id": client_id,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": jwt,
        },
        verify=False,
    )
    if req.ok:
        print(req.json())
        return req.json()["access_token"]
    else:
        print(req.request.url)
        print(req.request.body)
        print(req.status_code)
        print(req.reason)
        print(req.headers)
        print(req.json())
    return ""


def main():
    with open("client_id") as f:
        client_id = f.read().strip()

    req = get_users()
    if not req.ok:
        print(req.status_code)
        print(req.url)
        print(req.request.body)
        print(req.headers)

        ticket = ""
        for auth in [header.strip() for header in req.headers["WWW-Authenticate"].split(",")]:
            if auth.startswith("ticket"):
                ticket = auth.split("=")[-1]
                break

        print("using ticket: " + ticket)

        alias = get_kid()
        with open("scim_rp_jks_pass") as f:
            jks_pass = f.read()

        jks_to_pkcs12("scim-rp.jks", "scim-rp.pkcs12", alias, jks_pass)
        pubcert, privkey = certkey_from_pkcs12("scim-rp.pkcs12", "scim-rp.pem", jks_pass)

        jwt = generate_jwt(alias, privkey, client_id)
        print(jwt)
        token = get_token(client_id, jwt, ticket)
        req = get_users(token)

        if req.ok:
            print(req.url)
            print(req.json())


def get_base_url():
    return os.environ.get("GLUU_BASE_URL", "https://demoexample.gluu.org")


if __name__ == "__main__":
    main()
