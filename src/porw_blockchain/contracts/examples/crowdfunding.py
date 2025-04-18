"""
Example crowdfunding contract for the PoRW blockchain.

This contract implements a simple crowdfunding campaign where users can
contribute funds, and the campaign creator can withdraw the funds if the
goal is reached before the deadline.
"""

def initialize(goal, deadline):
    """
    Initialize the crowdfunding contract.
    
    Args:
        goal: The funding goal in PORW tokens.
        deadline: The deadline timestamp.
    """
    # Store campaign metadata
    context.set_storage("creator", context.get_sender())
    context.set_storage("goal", goal)
    context.set_storage("deadline", deadline)
    context.set_storage("total_raised", 0)
    context.set_storage("state", "active")  # active, successful, or failed
    
    # Log initialization
    context.log(f"Initialized crowdfunding campaign with goal {goal} and deadline {deadline}")
    
    # Emit event
    context.emit_event("CampaignCreated", {
        "creator": context.get_sender(),
        "goal": goal,
        "deadline": deadline
    })


def contribute():
    """
    Contribute funds to the campaign.
    
    Returns:
        True if the contribution was successful, False otherwise.
    """
    # Check if the campaign is active
    state = context.get_storage("state")
    if state != "active":
        context.log(f"Contribution failed: campaign is not active (state: {state})")
        return False
    
    # Check if the deadline has passed
    deadline = context.get_storage("deadline")
    current_time = context.get_timestamp()
    if current_time > deadline:
        context.log(f"Contribution failed: deadline has passed ({current_time} > {deadline})")
        return False
    
    # Get the contribution amount
    amount = context.get_value()
    if amount <= 0:
        context.log(f"Contribution failed: invalid amount ({amount})")
        return False
    
    # Update total raised
    total_raised = context.get_storage("total_raised") or 0
    context.set_storage("total_raised", total_raised + amount)
    
    # Update contributor's balance
    sender = context.get_sender()
    contributor_balance = context.get_storage(f"contributions.{sender}") or 0
    context.set_storage(f"contributions.{sender}", contributor_balance + amount)
    
    # Log contribution
    context.log(f"Received contribution of {amount} from {sender}")
    
    # Emit event
    context.emit_event("Contribution", {
        "contributor": sender,
        "amount": amount,
        "total_raised": total_raised + amount
    })
    
    return True


def check_goal_reached():
    """
    Check if the funding goal has been reached.
    
    Returns:
        True if the goal has been reached, False otherwise.
    """
    # Check if the campaign is active
    state = context.get_storage("state")
    if state != "active":
        return state == "successful"
    
    # Get campaign data
    total_raised = context.get_storage("total_raised") or 0
    goal = context.get_storage("goal")
    
    # Check if the goal has been reached
    if total_raised >= goal:
        context.set_storage("state", "successful")
        
        # Log success
        context.log(f"Campaign goal reached: {total_raised} >= {goal}")
        
        # Emit event
        context.emit_event("GoalReached", {
            "total_raised": total_raised,
            "goal": goal
        })
        
        return True
    
    return False


def check_deadline_passed():
    """
    Check if the deadline has passed.
    
    Returns:
        True if the deadline has passed, False otherwise.
    """
    # Check if the campaign is active
    state = context.get_storage("state")
    if state != "active":
        return True
    
    # Get campaign data
    deadline = context.get_storage("deadline")
    current_time = context.get_timestamp()
    
    # Check if the deadline has passed
    if current_time > deadline:
        # Check if the goal was reached
        if not check_goal_reached():
            context.set_storage("state", "failed")
            
            # Log failure
            context.log(f"Campaign failed: deadline passed and goal not reached")
            
            # Emit event
            context.emit_event("CampaignFailed", {
                "total_raised": context.get_storage("total_raised") or 0,
                "goal": context.get_storage("goal")
            })
        
        return True
    
    return False


def withdraw():
    """
    Withdraw funds from the campaign.
    
    Returns:
        True if the withdrawal was successful, False otherwise.
    """
    # Check if the sender is the creator
    sender = context.get_sender()
    creator = context.get_storage("creator")
    if sender != creator:
        context.log(f"Withdrawal failed: sender {sender} is not the creator {creator}")
        return False
    
    # Check if the campaign is successful
    if not check_goal_reached():
        context.log(f"Withdrawal failed: campaign goal not reached")
        return False
    
    # Get the amount to withdraw
    amount = context.get_storage("total_raised") or 0
    if amount <= 0:
        context.log(f"Withdrawal failed: no funds to withdraw")
        return False
    
    # Reset the total raised
    context.set_storage("total_raised", 0)
    
    # Log withdrawal
    context.log(f"Withdrew {amount} to {sender}")
    
    # Emit event
    context.emit_event("Withdrawal", {
        "recipient": sender,
        "amount": amount
    })
    
    return True


def refund():
    """
    Refund a contributor's funds.
    
    Returns:
        True if the refund was successful, False otherwise.
    """
    # Check if the campaign has failed
    check_deadline_passed()
    state = context.get_storage("state")
    if state != "failed":
        context.log(f"Refund failed: campaign is not in failed state (state: {state})")
        return False
    
    # Get the contributor's balance
    sender = context.get_sender()
    amount = context.get_storage(f"contributions.{sender}") or 0
    if amount <= 0:
        context.log(f"Refund failed: no funds to refund for {sender}")
        return False
    
    # Reset the contributor's balance
    context.set_storage(f"contributions.{sender}", 0)
    
    # Log refund
    context.log(f"Refunded {amount} to {sender}")
    
    # Emit event
    context.emit_event("Refund", {
        "contributor": sender,
        "amount": amount
    })
    
    return True


def get_campaign_info():
    """
    Get information about the campaign.
    
    Returns:
        A dictionary with campaign information.
    """
    # Check if the deadline has passed
    check_deadline_passed()
    
    # Return campaign information
    return {
        "creator": context.get_storage("creator"),
        "goal": context.get_storage("goal"),
        "deadline": context.get_storage("deadline"),
        "total_raised": context.get_storage("total_raised") or 0,
        "state": context.get_storage("state"),
        "current_time": context.get_timestamp()
    }


def get_contribution(contributor):
    """
    Get the contribution amount for a specific contributor.
    
    Args:
        contributor: The address of the contributor.
        
    Returns:
        The contribution amount.
    """
    return context.get_storage(f"contributions.{contributor}") or 0
