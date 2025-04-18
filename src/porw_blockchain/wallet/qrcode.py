# src/porw_blockchain/wallet/qrcode.py
"""
QR code functionality for the PoRW blockchain wallet.

This module provides functionality for generating and scanning QR codes
for payment requests and other wallet operations.
"""

import json
import logging
import re
import urllib.parse
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple, Union

# Configure logger
logger = logging.getLogger(__name__)


class QRCodeType(Enum):
    """Types of QR codes supported by the wallet."""
    PAYMENT_REQUEST = "payment"
    ADDRESS_ONLY = "address"
    CONTACT_CARD = "contact"
    TRANSACTION = "transaction"
    WALLET_CONNECT = "connect"


@dataclass
class PaymentRequest:
    """Payment request data structure."""
    address: str
    amount: Optional[float] = None
    memo: Optional[str] = None
    label: Optional[str] = None
    expires: Optional[int] = None  # Unix timestamp
    request_id: Optional[str] = None


class QRCodeError(Exception):
    """Exception raised for QR code errors."""
    pass


class QRCodeGenerator:
    """Generator for QR codes."""

    @staticmethod
    def generate_payment_request_data(payment_request: PaymentRequest) -> str:
        """
        Generate data for a payment request QR code.

        Args:
            payment_request: Payment request data

        Returns:
            QR code data string
        """
        # Validate address
        if not payment_request.address or not payment_request.address.startswith("porw1"):
            raise QRCodeError("Invalid PoRW address")

        # Build URI
        uri = f"porw:{payment_request.address}"
        params = {}

        if payment_request.amount is not None:
            if payment_request.amount <= 0:
                raise QRCodeError("Amount must be greater than 0")
            params["amount"] = str(payment_request.amount)

        if payment_request.memo:
            params["memo"] = payment_request.memo

        if payment_request.label:
            params["label"] = payment_request.label

        if payment_request.expires:
            params["expires"] = str(payment_request.expires)

        if payment_request.request_id:
            params["request_id"] = payment_request.request_id

        # Add parameters to URI if any
        if params:
            query_string = urllib.parse.urlencode(params)
            uri = f"{uri}?{query_string}"

        return uri

    @staticmethod
    def generate_address_only_data(address: str) -> str:
        """
        Generate data for an address-only QR code.

        Args:
            address: PoRW address

        Returns:
            QR code data string
        """
        # Validate address
        if not address or not address.startswith("porw1"):
            raise QRCodeError("Invalid PoRW address")

        return address

    @staticmethod
    def generate_contact_card_data(
        name: str,
        address: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        notes: Optional[str] = None
    ) -> str:
        """
        Generate data for a contact card QR code.

        Args:
            name: Contact name
            address: PoRW address
            email: Contact email
            phone: Contact phone
            notes: Additional notes

        Returns:
            QR code data string
        """
        # Validate address
        if not address or not address.startswith("porw1"):
            raise QRCodeError("Invalid PoRW address")

        # Create contact data
        contact_data = {
            "type": QRCodeType.CONTACT_CARD.value,
            "name": name,
            "address": address
        }

        if email:
            contact_data["email"] = email

        if phone:
            contact_data["phone"] = phone

        if notes:
            contact_data["notes"] = notes

        # Convert to JSON
        return json.dumps(contact_data)

    @staticmethod
    def generate_transaction_data(transaction: Dict[str, Any]) -> str:
        """
        Generate data for a transaction QR code.

        Args:
            transaction: Transaction data

        Returns:
            QR code data string
        """
        # Validate transaction
        if not transaction.get("id") or not transaction.get("sender") or not transaction.get("recipient"):
            raise QRCodeError("Invalid transaction data")

        # Create transaction data
        tx_data = {
            "type": QRCodeType.TRANSACTION.value,
            "transaction": transaction
        }

        # Convert to JSON
        return json.dumps(tx_data)

    @staticmethod
    def generate_wallet_connect_data(
        node_url: str,
        public_key: str,
        chain_id: str = "mainnet",
        protocol_version: str = "1.0"
    ) -> str:
        """
        Generate data for a wallet connect QR code.

        Args:
            node_url: Node URL
            public_key: Public key for encryption
            chain_id: Chain ID (default: "mainnet")
            protocol_version: Protocol version (default: "1.0")

        Returns:
            QR code data string
        """
        # Create wallet connect data
        connect_data = {
            "type": QRCodeType.WALLET_CONNECT.value,
            "url": node_url,
            "key": public_key,
            "chain": chain_id,
            "version": protocol_version
        }

        # Convert to JSON
        return json.dumps(connect_data)


class QRCodeParser:
    """Parser for QR codes."""

    @staticmethod
    def parse_qr_data(qr_data: str) -> Tuple[QRCodeType, Dict[str, Any]]:
        """
        Parse QR code data.

        Args:
            qr_data: QR code data string

        Returns:
            Tuple containing the QR code type and parsed data

        Raises:
            QRCodeError: If the QR code data is invalid or unsupported
        """
        try:
            # Check if it's a PoRW URI
            if qr_data.startswith("porw:"):
                return QRCodeParser._parse_porw_uri(qr_data)

            # Check if it's a plain address
            if qr_data.startswith("porw1"):
                return QRCodeType.ADDRESS_ONLY, {"address": qr_data}

            # Try to parse as JSON
            try:
                data = json.loads(qr_data)
                if isinstance(data, dict) and "type" in data:
                    qr_type = data.get("type")
                    if qr_type == QRCodeType.CONTACT_CARD.value:
                        return QRCodeType.CONTACT_CARD, data
                    elif qr_type == QRCodeType.TRANSACTION.value:
                        return QRCodeType.TRANSACTION, data
                    elif qr_type == QRCodeType.WALLET_CONNECT.value:
                        return QRCodeType.WALLET_CONNECT, data
            except json.JSONDecodeError:
                pass

            # Unsupported QR code
            raise QRCodeError("Unsupported QR code format")
        except Exception as e:
            logger.error(f"Error parsing QR code data: {e}")
            raise QRCodeError(f"Error parsing QR code data: {e}")

    @staticmethod
    def _parse_porw_uri(uri: str) -> Tuple[QRCodeType, Dict[str, Any]]:
        """
        Parse a PoRW URI.

        Args:
            uri: PoRW URI string

        Returns:
            Tuple containing the QR code type and parsed data

        Raises:
            QRCodeError: If the URI is invalid
        """
        # Parse URI
        match = re.match(r"porw:([a-zA-Z0-9]+)(\?(.*))?", uri)
        if not match:
            raise QRCodeError("Invalid PoRW URI")

        address = match.group(1)
        query_string = match.group(3)

        # Parse query parameters
        params = {}
        if query_string:
            params = dict(urllib.parse.parse_qsl(query_string))

        # Create payment request
        payment_request = {
            "address": address
        }

        if "amount" in params:
            try:
                payment_request["amount"] = float(params["amount"])
            except ValueError:
                raise QRCodeError("Invalid amount in payment request")

        if "memo" in params:
            payment_request["memo"] = params["memo"]

        if "label" in params:
            payment_request["label"] = params["label"]

        if "expires" in params:
            try:
                payment_request["expires"] = int(params["expires"])
            except ValueError:
                raise QRCodeError("Invalid expiration timestamp in payment request")

        if "request_id" in params:
            payment_request["request_id"] = params["request_id"]

        return QRCodeType.PAYMENT_REQUEST, payment_request


class QRCodeScanner:
    """
    Scanner for QR codes.
    
    This class provides functionality for scanning QR codes using
    the device camera and processing the scanned data.
    """

    def __init__(self):
        """Initialize the QR code scanner."""
        # Check if required libraries are available
        try:
            import cv2
            from pyzbar import pyzbar
            self.cv2 = cv2
            self.pyzbar = pyzbar
            self.scanner_available = True
        except ImportError:
            logger.warning("QR code scanning libraries not available. Install with: pip install opencv-python pyzbar")
            self.scanner_available = False

    def scan_from_camera(self, camera_index: int = 0, timeout: int = 30) -> Optional[str]:
        """
        Scan a QR code from the camera.

        Args:
            camera_index: Camera index (default: 0)
            timeout: Timeout in seconds (default: 30)

        Returns:
            Scanned QR code data, or None if no QR code was scanned

        Raises:
            QRCodeError: If scanning fails or is not available
        """
        if not self.scanner_available:
            raise QRCodeError("QR code scanning libraries not available")

        try:
            # Open camera
            cap = self.cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                raise QRCodeError(f"Could not open camera {camera_index}")

            # Set timeout
            start_time = self.cv2.getTickCount()
            timeout_ticks = timeout * self.cv2.getTickFrequency()

            while True:
                # Check timeout
                current_time = self.cv2.getTickCount()
                if (current_time - start_time) / self.cv2.getTickFrequency() > timeout:
                    break

                # Read frame
                ret, frame = cap.read()
                if not ret:
                    continue

                # Decode QR code
                decoded_objects = self.pyzbar.decode(frame)
                for obj in decoded_objects:
                    # Close camera
                    cap.release()
                    
                    # Return QR code data
                    return obj.data.decode('utf-8')

                # Display frame
                self.cv2.imshow('QR Code Scanner', frame)
                
                # Check for key press
                if self.cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            # Close camera
            cap.release()
            self.cv2.destroyAllWindows()
            
            return None
        except Exception as e:
            logger.error(f"Error scanning QR code: {e}")
            raise QRCodeError(f"Error scanning QR code: {e}")

    def scan_from_image(self, image_path: str) -> Optional[str]:
        """
        Scan a QR code from an image.

        Args:
            image_path: Path to the image file

        Returns:
            Scanned QR code data, or None if no QR code was found

        Raises:
            QRCodeError: If scanning fails or is not available
        """
        if not self.scanner_available:
            raise QRCodeError("QR code scanning libraries not available")

        try:
            # Read image
            image = self.cv2.imread(image_path)
            if image is None:
                raise QRCodeError(f"Could not read image: {image_path}")

            # Decode QR code
            decoded_objects = self.pyzbar.decode(image)
            for obj in decoded_objects:
                return obj.data.decode('utf-8')

            return None
        except Exception as e:
            logger.error(f"Error scanning QR code from image: {e}")
            raise QRCodeError(f"Error scanning QR code from image: {e}")


def generate_payment_qr_code(
    address: str,
    amount: Optional[float] = None,
    memo: Optional[str] = None,
    label: Optional[str] = None,
    expires: Optional[int] = None,
    request_id: Optional[str] = None
) -> str:
    """
    Generate a payment request QR code.

    Args:
        address: Recipient address
        amount: Payment amount
        memo: Payment memo
        label: Payment label
        expires: Expiration timestamp
        request_id: Request ID

    Returns:
        QR code data string
    """
    payment_request = PaymentRequest(
        address=address,
        amount=amount,
        memo=memo,
        label=label,
        expires=expires,
        request_id=request_id
    )
    return QRCodeGenerator.generate_payment_request_data(payment_request)


def parse_payment_qr_code(qr_data: str) -> Optional[PaymentRequest]:
    """
    Parse a payment request QR code.

    Args:
        qr_data: QR code data string

    Returns:
        Payment request data, or None if the QR code is not a payment request
    """
    try:
        qr_type, data = QRCodeParser.parse_qr_data(qr_data)
        if qr_type == QRCodeType.PAYMENT_REQUEST:
            return PaymentRequest(
                address=data.get("address"),
                amount=data.get("amount"),
                memo=data.get("memo"),
                label=data.get("label"),
                expires=data.get("expires"),
                request_id=data.get("request_id")
            )
        elif qr_type == QRCodeType.ADDRESS_ONLY:
            return PaymentRequest(address=data.get("address"))
        return None
    except Exception as e:
        logger.error(f"Error parsing payment QR code: {e}")
        return None
