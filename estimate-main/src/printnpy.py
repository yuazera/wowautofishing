import os
import numpy as np

# Construct the full path to the .npy file
file_path = r'D:\autofishing\wowautofishing\estimate-main\src\data\US\sp500\baseline_data_sp500.npy'

# 添加路径检查
print(f"Checking file path: {file_path}")
if not os.path.exists(file_path):
    print(f"Error: File not found at {file_path}")
    print(f"Current working directory: {os.getcwd()}")
    print("Available files in current directory:")
    try:
        for f in os.listdir(os.path.dirname(file_path)):
            print(f"- {f}")
    except FileNotFoundError:
        print(f"Directory {os.path.dirname(file_path)} does not exist")
    exit(1)

try:
    # Load .npy file
    data_dict = np.load(file_path, allow_pickle=True).item()
    
    # Access specific stock data
    stock_data = list(data_dict.items())[:20]

    # Print data
    for stock, data in stock_data:
        print(f"Stock: {stock}")
        print(data)
except Exception as e:
    print(f"Error loading file: {str(e)}")