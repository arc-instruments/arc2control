import glob
import os.path
from base64 import b64decode

from . import constants

from PyQt6.QtCore import QStandardPaths
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature


def discoverFirmwares(acceptUnverified=False):

    basePaths = QStandardPaths.standardLocations(\
        QStandardPaths.StandardLocation.AppDataLocation)

    paths = [os.path.join(p, 'firmware') for p in basePaths]

    pubkey = load_pem_public_key(constants.ARCFW_PUBKEY.encode(), default_backend())

    allfws = {}
    for p in reversed(paths):
        fws = glob.glob(os.path.join(p, '*.bin'))
        for fw in fws:
            try:
                sig = b64decode(open('%s.txt' % fw, 'r').read())
                pubkey.verify(sig, open(fw, 'rb').read(), ec.ECDSA(hashes.SHA256()))
                # an exception will be thrown if verification fails
                # so this will never be reached
                verified = True
            except (InvalidSignature, FileNotFoundError):
                verified = False

            if verified or acceptUnverified:
                allfws[os.path.basename(fw)] = { 'path': fw, 'verified': verified }

    return allfws
