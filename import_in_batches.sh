#!/bin/bash

# This script runs the import_all_incremental.py script repeatedly
# to import data in batches

# Parameters
BATCH_SIZE=20
NUM_BATCHES=5
IMPORT_TYPE="all"  # can be "all", "improvements", "accounts", or "images"

# Display settings
echo "Starting batch import with the following settings:"
echo "  Import type: $IMPORT_TYPE"
echo "  Batch size: $BATCH_SIZE"
echo "  Number of batches: $NUM_BATCHES"
echo ""

# Import the batches
for ((i=1; i<=$NUM_BATCHES; i++)); do
    echo "Running batch $i of $NUM_BATCHES..."
    python import_all_incremental.py $IMPORT_TYPE $BATCH_SIZE
    
    # Check if the import was successful
    if [ $? -ne 0 ]; then
        echo "Error: Batch $i failed! Stopping import process."
        exit 1
    fi
    
    echo "Batch $i completed successfully."
    echo ""
    
    # Sleep briefly to allow any background processing to complete
    sleep 1
done

echo "All batches completed successfully!"
echo "Total records imported: $((BATCH_SIZE * NUM_BATCHES)) per data type"
