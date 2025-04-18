# Methods to add to the Wallet class for hardware wallet support

def connect_hardware_wallet(self, wallet_type: HardwareWalletType, derivation_path: str = "m/44'/0'/0'/0/0") -> bool:
    """
    Connect to a hardware wallet.

    Args:
        wallet_type: The type of hardware wallet to connect to.
        derivation_path: The BIP32 derivation path to use (default: "m/44'/0'/0'/0/0").

    Returns:
        True if connection was successful, False otherwise.
    """
    logger.info(f"Connecting to {wallet_type.value} hardware wallet")

    # Connect to hardware wallet
    if self.hardware_wallet_manager.connect_wallet(wallet_type):
        # Get address from hardware wallet
        try:
            address = self.hardware_wallet_manager.get_wallet_address(
                derivation_path=derivation_path,
                testnet=self.testnet
            )

            # Set wallet state
            self.using_hardware_wallet = True
            self.hardware_wallet_type = wallet_type
            self.hardware_derivation_path = derivation_path
            self.address = address

            # Get device info
            device_info = self.hardware_wallet_manager.get_device_info()
            logger.info(f"Connected to {device_info['type']} {device_info['model']} with address {address}")

            # Initialize wallet components that don't require private key
            if self.is_connected:
                asyncio.create_task(self.balance_tracker.track_address(self.address))

            return True
        except Exception as e:
            logger.error(f"Error getting address from hardware wallet: {e}")
            self.hardware_wallet_manager.disconnect_wallet(wallet_type)
            return False
    else:
        logger.error(f"Failed to connect to {wallet_type.value} hardware wallet")
        return False

def disconnect_hardware_wallet(self) -> None:
    """
    Disconnect from the hardware wallet.
    """
    if self.using_hardware_wallet and self.hardware_wallet_type:
        logger.info(f"Disconnecting from {self.hardware_wallet_type.value} hardware wallet")
        self.hardware_wallet_manager.disconnect_wallet(self.hardware_wallet_type)
        
        # Reset hardware wallet state
        self.using_hardware_wallet = False
        self.hardware_wallet_type = None
        self.hardware_derivation_path = None
        self.address = None

def is_hardware_wallet_connected(self) -> bool:
    """
    Check if a hardware wallet is connected.

    Returns:
        True if a hardware wallet is connected, False otherwise.
    """
    return self.using_hardware_wallet and self.hardware_wallet_type is not None and \
           self.hardware_wallet_manager.is_wallet_connected(self.hardware_wallet_type)

def get_hardware_wallet_info(self) -> Optional[Dict[str, Any]]:
    """
    Get information about the connected hardware wallet.

    Returns:
        A dictionary containing hardware wallet information, or None if no hardware wallet is connected.
    """
    if not self.is_hardware_wallet_connected():
        return None

    try:
        device_info = self.hardware_wallet_manager.get_device_info(self.hardware_wallet_type)
        return {
            "type": self.hardware_wallet_type.value,
            "model": device_info.get("model", "Unknown"),
            "firmware_version": device_info.get("firmware_version", "Unknown"),
            "address": self.address,
            "derivation_path": self.hardware_derivation_path
        }
    except Exception as e:
        logger.error(f"Error getting hardware wallet info: {e}")
        return None
