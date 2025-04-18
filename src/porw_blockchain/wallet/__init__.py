# src/porw_blockchain/wallet/__init__.py
"""
Wallet package for the PoRW blockchain.

This package provides wallet functionality including key management,
transaction creation, and balance checking.
"""

from .key_management import (
    create_new_wallet,
    save_wallet,
    load_wallet,
    list_wallets,
    create_wallet_backup,
    restore_wallet_from_backup,
    export_wallet_to_json,
    import_wallet_from_json,
    export_wallet_to_paper_backup
)

from .main import Wallet
from .hardware import (
    HardwareWalletType,
    HardwareWalletError,
    HardwareWalletInterface,
    LedgerWallet,
    TrezorWallet,
    HardwareWalletManager,
    hardware_wallet_manager
)

from .qrcode import (
    QRCodeType,
    QRCodeError,
    QRCodeGenerator,
    QRCodeParser,
    QRCodeScanner,
    PaymentRequest,
    generate_payment_qr_code,
    parse_payment_qr_code
)

__all__ = [
    # Main wallet class
    'Wallet',

    # Key management functions
    'create_new_wallet',
    'save_wallet',
    'load_wallet',
    'list_wallets',
    'create_wallet_backup',
    'restore_wallet_from_backup',
    'export_wallet_to_json',
    'import_wallet_from_json',
    'export_wallet_to_paper_backup',

    # Hardware wallet classes
    'HardwareWalletType',
    'HardwareWalletError',
    'HardwareWalletInterface',
    'LedgerWallet',
    'TrezorWallet',
    'HardwareWalletManager',
    'hardware_wallet_manager',

    # QR code classes and functions
    'QRCodeType',
    'QRCodeError',
    'QRCodeGenerator',
    'QRCodeParser',
    'QRCodeScanner',
    'PaymentRequest',
    'generate_payment_qr_code',
    'parse_payment_qr_code'
]
