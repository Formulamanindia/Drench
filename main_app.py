import streamlit as st
import pandas as pd
import io
import pdfplumber

# --- Configuration Management (Uses st.session_state) ---

# Initialize the list of accounts if not already in session state
if 'account_list' not in st.session_state:
    st.session_state.account_list = [
        "Drench", "Drench India", "Sparsh", "Sparsh SC", 
        "Shine Arc", "Shopforher", "Ansh Ent.", "Meesho India" 
    ]

# Function to read and process the uploaded PDF files using pdfplumber
def process_uploads(uploaded_files_map):
    all_data = []
    
    for account_name, file in uploaded_files_map.items():
        if file is not None:
            st.info(f"Processing PDF for: **{account_name}**...")
            
            try:
                # Open the PDF file using pdfplumber from the uploaded buffer
                with pdfplumber.open(file) as pdf:
                    
                    account_dfs = []
                    
                    # Iterate through all pages in the PDF
                    for page in pdf.pages:
                        # Extract all detected tables on the page
                        tables = page.extract_tables() 
                        
                        for table in tables:
                            # Convert the extracted table (list of lists) into a DataFrame
                            if table and len(table) > 1:
                                # Use the first row as headers, and the rest as data
                                df_page = pd.DataFrame(table[1:], columns=table[0])
                                account_dfs.append(df_page)

                    # Concatenate all extracted tables from all pages for this account
                    if not account_dfs:
                        st.warning(f"Could not extract any tables from {account_name}'s PDF. Skipping.")
                        continue
                        
                    df = pd.concat(account_dfs, ignore_index=True)
                    
                    # 4. Add the mandatory Account Name column
                    df['Source_Account'] = account_name
                    
                    # --- CRITICAL: STANDARDIZATION & CLEANING STEP ---
                    # **You MUST update these column names to match what pdfplumber extracts**
                    # Check your actual PDF output and replace the example names below.
                    # Common names for Meesho picklist data:
                    df.rename(columns={
                        'Product ID': 'SKU', 
                        'Qty to Ship': 'Qty', 
                        'Order Item ID': 'Order ID'
                    }, inplace=True, errors='ignore') # 'errors=ignore' prevents crash if column doesn't exist
                    
                    # Clean up data and validate
                    if 'SKU' in df.columns and 'Qty' in df.columns:
                        # Convert Quantity to numeric, coercing errors to 0
                        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0).astype(int)
                        # Remove rows where SKU is missing (e.g., empty table rows)
                        df.dropna(subset=['SKU'], inplace=True) 
                        all_data.append(df)
                        st.success(f"Successfully extracted and loaded data from **{account_name}**.")
                    else:
                        st.error(f"Extraction failed for {account_name}. Missing required columns (SKU or Qty) after renaming.")
                        
            except Exception as e:
                st.error(f"An unexpected error occurred processing {account_name}'s PDF: {e}")

    return all_data

# --- Streamlit Layout ---
st.set_page_config(layout="wide")
st.title("🛍️ Meesho PDF Picklist Merger & Configurator")
st.caption("Converts multi-account PDF picklists to a single consolidated CSV.")

# Create the two tabs
tab1, tab2 = st.tabs(["🚀 Order Processing", "⚙️ Configuration"])

# =========================================================
# TAB 1: Order Processing (The Main Functionality)
# =========================================================
with tab1:
    st.header("Upload PDF Picklists by Account")
    
    uploaded_files_map = {}
    
    # Create the upload options dynamically using 3 columns
    cols = st.columns(3) 
    
    for i, account_name in enumerate(st.session_state.account_list):
        # Cycle through the 3 columns
        with cols[i % 3]: 
            key = f"file_uploader_{account_name}"
            uploaded_files_map[account_name] = st.file_uploader(
                f"**{i+1}. {account_name}**", 
                type=['pdf'],
                key=key
            )
            
    st.markdown("---")
    
    if st.button("Submit & Merge Picklists", type="primary"):
        if any(uploaded_files_map.values()):
            
            combined_list = process_uploads(uploaded_files_map)
            
            if combined_list:
                combined_df = pd.concat(combined_list, ignore_index=True)
                
                # Aggregation/Grouping: Group by SKU and sum quantities
                final_picklist = combined_df.groupby('SKU').agg(
                    Total_Quantity=('Qty', 'sum'),
                    # List unique accounts involved
                    Source_Accounts=('Source_Account', lambda x: ', '.join(x.unique())),
                    # List all unique Order IDs involved (for tracking)
                    Orders_Involved=('Order ID', lambda x: ', '.join(x.dropna().astype(str).unique()))
                ).reset_index()

                st.subheader("✅ Consolidated Picklist Ready")
                st.dataframe(final_picklist)
                

                # Downloadable Result in CSV format
                csv_file = final_picklist.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Merged Picklist (CSV)",
                    data=csv_file,
                    file_name='merged_meesho_picklist.csv',
                    mime='text/csv',
                )
            else:
                st.warning("No files were successfully processed. Please ensure your PDFs contain clear, text-based tables.")
        else:
            st.warning("Please upload at least one PDF picklist file to proceed.")


# =========================================================
# TAB 2: Configuration (Adding/Removing Accounts)
# =========================================================
with tab2:
    st.header("Account Configuration")
    st.write("Manage the list of accounts that appear in the upload section. Changes are saved for your session.")
    
    # Function to add a new account
    def add_account():
        if st.session_state.new_account_name and st.session_state.new_account_name not in st.session_state.account_list:
            st.session_state.account_list.append(st.session_state.new_account_name)
            st.success(f"Added '{st.session_state.new_account_name}' to the list.")
            st.session_state.new_account_name = "" # Clear input box

    st.subheader("➕ Add New Account")
    st.text_input("Enter new Account Name (e.g., 'New Seller Name')", key='new_account_name')
    st.button("Add Account", on_click=add_account)
    
    st.markdown("---")

    st.subheader("🗑️ Existing Accounts")
    current_list = st.session_state.account_list.copy()

    if current_list:
        cols_config = st.columns(3)
        for i, account in enumerate(current_list):
            with cols_config[i % 3]:
                # Button to remove the account
                if st.button(f"Remove {account}", key=f"remove_{account}"):
                    st.session_state.account_list.remove(account)
                    st.experimental_rerun() # Rerun to update the display
    else:
        st.info("No accounts configured yet.")

    st.markdown("---")
    st.info(f"**Current number of configured accounts:** {len(st.session_state.account_list)}")
