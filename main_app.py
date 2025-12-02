import streamlit as st
import pandas as pd
import io

# --- Configuration Management (Using st.session_state) ---
# Initialize the list of accounts if not already in session state
if 'account_list' not in st.session_state:
    st.session_state.account_list = [
        "Drench", "Drench India", "Sparsh", "Sparsh SC", 
        "Shine Arc", "Shopforher", "Ansh Ent.", "Meesho India" 
    ]

# Function to read and process the uploaded files
def process_uploads(uploaded_files_map):
    all_data = []
    
    for account_name, file in uploaded_files_map.items():
        if file is not None:
            try:
                # Determine file type and read data
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                elif file.name.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(file)
                else:
                    st.warning(f"Skipping {file.name}: Unsupported file type.")
                    continue
                
                # Add the mandatory Account Name column
                df['Source_Account'] = account_name
                
                # --- IMPORTANT: Standardize Column Names Here ---
                # Example:
                # df.rename(columns={'Product ID': 'SKU', 'Quantity': 'Qty', ...}, inplace=True)
                
                # Ensure the key columns (SKU, Qty) exist after standardization
                # Replace 'SKU' and 'Qty' with your actual standardized column names
                if 'SKU' in df.columns and 'Qty' in df.columns:
                    all_data.append(df)
                else:
                    st.error(f"Error in {account_name}: Missing required columns (SKU, Qty) after standardization.")
                    
            except Exception as e:
                st.error(f"Error processing {account_name}'s file: {e}")

    return all_data

# --- Streamlit Layout ---
st.title("🛍️ Meesho Picklist Merger & Configurator")
st.caption("Developed for consolidated order processing across multiple seller accounts.")

# Create the two tabs: 'Order Processing' and 'Configuration'
tab1, tab2 = st.tabs(["🚀 Order Processing", "⚙️ Configuration"])

# =========================================================
# TAB 1: Order Processing (The Main Functionality)
# =========================================================
with tab1:
    st.header("Upload Picklists by Account")
    
    uploaded_files_map = {}
    
    # Create the upload options dynamically based on the current session state list
    # We use columns for better visual layout
    cols = st.columns(3) # Use 3 columns to organize the 8 uploads
    
    for i, account_name in enumerate(st.session_state.account_list):
        with cols[i % 3]: # Cycle through the 3 columns
            key = f"file_uploader_{account_name}"
            uploaded_files_map[account_name] = st.file_uploader(
                f"**{i+1}. {account_name}**", 
                type=['csv', 'xlsx'],
                key=key
            )
            
    st.markdown("---")
    
    if st.button("Submit & Merge Picklists", type="primary"):
        # Check if any file was uploaded
        if any(uploaded_files_map.values()):
            
            # Step 1: Process and combine the data
            combined_list = process_uploads(uploaded_files_map)
            
            if combined_list:
                combined_df = pd.concat(combined_list, ignore_index=True)
                
                # Step 2: Aggregation/Grouping (The core merging logic)
                # Group by SKU and sum the quantities from all accounts
                final_picklist = combined_df.groupby('SKU').agg(
                    Total_Quantity=('Qty', 'sum'),
                    Source_Accounts=('Source_Account', lambda x: ', '.join(x.unique())),
                    Orders_Involved=('Order ID', lambda x: ', '.join(x.astype(str).unique())) # Assuming 'Order ID' is a standardized column
                ).reset_index()

                st.subheader("✅ Consolidated Picklist Ready")
                st.dataframe(final_picklist)

                # Step 3: Downloadable Result
                buffer = io.BytesIO()
                # Choose your preferred output format (CSV or Excel)
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    final_picklist.to_excel(writer, index=False, sheet_name='Merged_Picklist')
                
                st.download_button(
                    label="Download Merged Picklist (Excel)",
                    data=buffer,
                    file_name='merged_meesho_picklist.xlsx',
                    mime='application/vnd.ms-excel',
                )
            else:
                st.warning("No files were successfully processed. Please check file types and required columns.")
        else:
            st.warning("Please upload at least one picklist file to proceed.")


# =========================================================
# TAB 2: Configuration (Adding/Removing Accounts)
# =========================================================
with tab2:
    st.header("Account Configuration")
    st.write("Manage the list of accounts that appear in the upload section.")
    
    current_list = st.session_state.account_list.copy() # Work with a copy

    # Function to add a new account
    def add_account():
        if st.session_state.new_account_name and st.session_state.new_account_name not in st.session_state.account_list:
            st.session_state.account_list.append(st.session_state.new_account_name)
            st.success(f"Added '{st.session_state.new_account_name}' to the list.")
            st.session_state.new_account_name = "" # Clear input box

    # Input for adding a new account
    st.subheader("➕ Add New Account")
    st.text_input("Enter new Account Name (e.g., 'New Seller Name')", key='new_account_name', on_change=add_account)
    st.button("Add Account", on_click=add_account)
    
    st.markdown("---")

    # Display and allow removal of existing accounts
    st.subheader("🗑️ Existing Accounts")
    if current_list:
        cols_config = st.columns(3)
        for i, account in enumerate(current_list):
            with cols_config[i % 3]:
                # Button to remove the account
                if st.button(f"Remove {account}", key=f"remove_{account}"):
                    st.session_state.account_list.remove(account)
                    st.experimental_rerun() # Rerun to update the display immediately
    else:
        st.info("No accounts configured yet. Use the input box above to add some!")

    st.markdown("---")
    st.info(f"**Current number of configured accounts:** {len(st.session_state.account_list)}")
