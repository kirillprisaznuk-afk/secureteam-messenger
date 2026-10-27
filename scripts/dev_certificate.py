"""Generate an untracked, short-lived localhost development certificate.

Requires the development dependencies; never overwrites existing key material.
"""

import argparse
import datetime
import ipaddress
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def generate(directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    cert_path, key_path = directory / "localhost.pem", directory / "localhost.key"
    if cert_path.exists() or key_path.exists():
        raise FileExistsError("Certificate or key already exists; choose a new output directory")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=30))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    with key_path.open("xb") as stream:
        stream.write(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
    with cert_path.open("xb") as stream:
        stream.write(certificate.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("certs"))
    args = parser.parse_args()
    try:
        cert, key = generate(args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(
        f"Certificate: {cert}\nPrivate key: {key}\nLocal development only; expires after 30 days."
    )


if __name__ == "__main__":
    main()
