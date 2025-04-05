# src/porw_blockchain/rpc/routers/blocks.py
"""
API Router for block-related operations.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Adjust import paths based on project structure
from ...storage import crud
from ...storage.database import get_db # Use the dependency from main app setup
from ...core.structures import Block as BlockSchema # Use Pydantic model from core


# Create an API Router instance
router = APIRouter(
    prefix="/blocks",  # All routes in this file will start with /blocks
    tags=["Blocks"],   # Tag for OpenAPI documentation grouping
)


@router.get(
    "/latest",
    response_model=Optional[BlockSchema], # Response type based on Pydantic model
    summary="Get the latest block",
    description="Retrieves the block with the highest index from the blockchain.",
)
def read_latest_block(db: Session = Depends(get_db)):
    """
    API endpoint to retrieve the latest block added to the blockchain.
    Returns HTTP 404 if the blockchain is empty.
    """
    db_block = crud.get_latest_db_block(db=db)
    if db_block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blockchain is empty, no latest block found.",
        )
    # Pydantic automatically converts DbBlock to BlockSchema if fields match
    return db_block


@router.get(
    "/{block_index}",
    response_model=BlockSchema,
    summary="Get block by index",
    description="Retrieves a specific block using its numerical index.",
)
def read_block_by_index(block_index: int, db: Session = Depends(get_db)):
    """
    API endpoint to retrieve a block by its index.
    Returns HTTP 404 if no block with the given index exists.
    """
    # Add validation for index if needed (e.g., index >= 0)
    if block_index < 0:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Block index cannot be negative.",
         )

    db_block = crud.get_db_block_by_index(db=db, index=block_index)
    if db_block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with index {block_index} not found.",
        )
    return db_block


@router.get(
    "/hash/{block_hash}",
    response_model=BlockSchema,
    summary="Get block by hash",
    description="Retrieves a specific block using its SHA256 hash.",
)
def read_block_by_hash(block_hash: str, db: Session = Depends(get_db)):
    """
    API endpoint to retrieve a block by its hash.
    Returns HTTP 404 if no block with the given hash exists.
    """
    # Add validation for hash format if needed
    if len(block_hash) != 64: # Basic SHA256 length check
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid block hash format provided.",
         )

    db_block = crud.get_db_block_by_hash(db=db, block_hash=block_hash)
    if db_block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with hash {block_hash} not found.",
        )
    return db_block


# Placeholder for adding new blocks - Requires consensus logic integration
# @router.post("/", status_code=status.HTTP_201_CREATED, ...)
# async def submit_new_block(...) -> BlockSchema:
#    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)