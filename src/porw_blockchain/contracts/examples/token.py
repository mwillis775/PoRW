"""
Example ERC-20 like token contract for the PoRW blockchain.

This contract implements a simple token with transfer, approve, and transferFrom
functionality similar to the ERC-20 standard on Ethereum.
"""

# Token contract
def initialize(name, symbol, total_supply):
    """
    Initialize the token contract.
    
    Args:
        name: Name of the token.
        symbol: Symbol of the token.
        total_supply: Total supply of the token.
    """
    # Store token metadata
    context.set_storage("name", name)
    context.set_storage("symbol", symbol)
    context.set_storage("total_supply", total_supply)
    
    # Assign all tokens to the creator
    context.set_storage(f"balances.{context.get_sender()}", total_supply)
    
    # Log initialization
    context.log(f"Initialized token: {name} ({symbol}) with total supply {total_supply}")
    
    # Emit event
    context.emit_event("Initialized", {
        "name": name,
        "symbol": symbol,
        "total_supply": total_supply,
        "creator": context.get_sender()
    })


def name():
    """
    Get the name of the token.
    
    Returns:
        The name of the token.
    """
    return context.get_storage("name")


def symbol():
    """
    Get the symbol of the token.
    
    Returns:
        The symbol of the token.
    """
    return context.get_storage("symbol")


def total_supply():
    """
    Get the total supply of the token.
    
    Returns:
        The total supply of the token.
    """
    return context.get_storage("total_supply")


def balance_of(owner):
    """
    Get the balance of an address.
    
    Args:
        owner: The address to check.
        
    Returns:
        The balance of the address.
    """
    return context.get_storage(f"balances.{owner}") or 0


def allowance(owner, spender):
    """
    Get the amount of tokens that a spender is allowed to spend on behalf of an owner.
    
    Args:
        owner: The address that owns the tokens.
        spender: The address that can spend the tokens.
        
    Returns:
        The amount of tokens the spender is allowed to spend.
    """
    return context.get_storage(f"allowances.{owner}.{spender}") or 0


def transfer(to, amount):
    """
    Transfer tokens from the sender to another address.
    
    Args:
        to: The address to transfer to.
        amount: The amount to transfer.
        
    Returns:
        True if the transfer was successful, False otherwise.
    """
    sender = context.get_sender()
    
    # Check if the sender has enough tokens
    sender_balance = balance_of(sender)
    if sender_balance < amount:
        context.log(f"Transfer failed: insufficient balance ({sender_balance} < {amount})")
        return False
    
    # Update balances
    context.set_storage(f"balances.{sender}", sender_balance - amount)
    context.set_storage(f"balances.{to}", balance_of(to) + amount)
    
    # Log transfer
    context.log(f"Transferred {amount} tokens from {sender} to {to}")
    
    # Emit event
    context.emit_event("Transfer", {
        "from": sender,
        "to": to,
        "amount": amount
    })
    
    return True


def approve(spender, amount):
    """
    Approve a spender to spend tokens on behalf of the sender.
    
    Args:
        spender: The address that can spend the tokens.
        amount: The amount that can be spent.
        
    Returns:
        True if the approval was successful.
    """
    sender = context.get_sender()
    
    # Set allowance
    context.set_storage(f"allowances.{sender}.{spender}", amount)
    
    # Log approval
    context.log(f"Approved {spender} to spend {amount} tokens on behalf of {sender}")
    
    # Emit event
    context.emit_event("Approval", {
        "owner": sender,
        "spender": spender,
        "amount": amount
    })
    
    return True


def transfer_from(from_address, to, amount):
    """
    Transfer tokens from one address to another on behalf of a third party.
    
    Args:
        from_address: The address to transfer from.
        to: The address to transfer to.
        amount: The amount to transfer.
        
    Returns:
        True if the transfer was successful, False otherwise.
    """
    sender = context.get_sender()
    
    # Check if the sender is allowed to spend enough tokens
    allowed = allowance(from_address, sender)
    if allowed < amount:
        context.log(f"TransferFrom failed: insufficient allowance ({allowed} < {amount})")
        return False
    
    # Check if the from address has enough tokens
    from_balance = balance_of(from_address)
    if from_balance < amount:
        context.log(f"TransferFrom failed: insufficient balance ({from_balance} < {amount})")
        return False
    
    # Update balances
    context.set_storage(f"balances.{from_address}", from_balance - amount)
    context.set_storage(f"balances.{to}", balance_of(to) + amount)
    
    # Update allowance
    context.set_storage(f"allowances.{from_address}.{sender}", allowed - amount)
    
    # Log transfer
    context.log(f"Transferred {amount} tokens from {from_address} to {to} on behalf of {sender}")
    
    # Emit event
    context.emit_event("Transfer", {
        "from": from_address,
        "to": to,
        "amount": amount
    })
    
    return True
