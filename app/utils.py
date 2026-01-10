import hmac
import hashlib
import base64


def generate_signature(total_amount, transaction_uuid, product_code, secret_key):
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"

    hmac_sha256 = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    )

    signature = base64.b64encode(hmac_sha256.digest()).decode()
    return signature
