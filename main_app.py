import streamlit as st
import pandas as pd
import io
import tempfile
import os

# --- CRITICAL FIX: Explicitly set JAVA_HOME for tabula-py ---
# This path is common for packages installed via apt on Debian/Ubuntu systems
# (which Streamlit Cloud uses) and often fixes the "Java not found" issue.
# The path might vary slightly, but this is the most common path for JRE 11.
os.environ['JAVA_HOME'] = '/usr/lib/jvm/java-11-openjdk-amd64/' 
os.environ['PATH'] = os.environ['PATH'] + ':' + os.environ['JAVA_HOME'] + 'bin/'
# -------------------------------------------------------------

import tabula # Now the import should work as Java path is set

# The rest of your code follows...
# --- Configuration Management (Using st.session_state) ---
if 'account_list' not in st.session_state:
# ... (rest of your app code)
    st.session_state.account_list = [
        "Drench", "Drench India", "Sparsh", "Sparsh SC", 
        "Shine Arc", "Shopforher", "Ansh Ent.", "Meesho India" 
    ]

# Function to read and process the uploaded PDF files
def process_uploads(uploaded_files_map):
    all_data = []
    
    for account_name, file in uploaded_files_map.items():
        if file is not None:
            st.info(f"Processing PDF for: **{account_name}**...")
            
            # Streamlit file uploader returns a BytesIO object, but tabula-py often 
            # requires a temporary file path for reliable table extraction.
            try:
                # 1. Write uploaded file to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(file.getvalue())
                    tmp_file_path = tmp_file.name

                # 2. Extract tables using tabula-py
                # 'pages="all"' extracts tables from all pages
                # 'multiple_tables=True' returns a list of DataFrames if multiple tables are found
                dfs = tabula.read_pdf(tmp_file_path, pages="all", multiple_tables=True, guess=True)
                
                # Check if tables were successfully extracted
                if not dfs:
                    st.warning(f"Could not extract any tables from {account_name}'s PDF. Skipping.")
                    continue
                
                # 3. Concatenate all extracted tables into a single DataFrame for the account
                df = pd.concat(dfs, ignore_index=True)
                
                # 4. Add the mandatory Account Name column
                df['Source_Account'] = account_name
                
                # --- IMPORTANT: Standardize Column Names and Clean Data Here ---
                # **CRITICAL STEP:** Rename PDF headers (which may be messy) to standardized names.
                # You MUST replace the placeholder names below with the actual names you see in the PDF output.
                # Example:
                df.rename(columns={'Product_Code': 'SKU', 'Final Qty': 'Qty', 'Order Number': 'Order ID'}, inplace=True)
                
                # 5. Final validation and append
                # Replace 'SKU' and 'Qty' with your standardized column names
                if 'SKU' in df.columns and 'Qty' in df.columns:
                    # Clean up data types (e.g., ensure quantity is numeric)
                    df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0)
                    all_data.append(df)
                    st.success(f"Successfully extracted and loaded data from **{account_name}**.")
                else:
                    st.error(f"Error in {account_name}: Missing required columns ('SKU', 'Qty') after extraction/standardization. Check your PDF table format.")
                    
            except Exception as e:
                st.error(f"An unexpected error occurred processing {account_name}'s PDF: {e}")
            finally:
                # Clean up the temporary file
                if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)

    return all_data

# --- Streamlit Layout ---
st.title("🛍️ Meesho PDF Picklist Merger & Configurator")
st.caption("Converts PDF picklists to a consolidated CSV via table extraction.")

tab1, tab2 = st.tabs(["🚀 Order Processing", "⚙️ Configuration"])

# =========================================================
# TAB 1: Order Processing (Main Functionality)
# =========================================================
with tab1:
    st.header("Upload PDF Picklists by Account")
    
    uploaded_files_map = {}
    cols = st.columns(3) 
    
    for i, account_name in enumerate(st.session_state.account_list):
        with cols[i % 3]: 
            key = f"file_uploader_{account_name}"
            # Changed 'type' to accept only PDF files
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
                
                # Aggregation/Grouping (The core merging logic remains the same)
                # Group by SKU and sum the quantities from all accounts
                final_picklist = combined_df.groupby('SKU').agg(
                    Total_Quantity=('Qty', 'sum'),
                    Source_Accounts=('Source_Account', lambda x: ', '.join(x.unique())),
                    Orders_Involved=('Order ID', lambda x: ', '. join(x.astype(str).unique()))
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
# TAB 2: Configuration (Adding/Removing Accounts) - Remains the same
# =========================================================
with tab2:
    st.header("Account Configuration")
    st.write("Manage the list of accounts that appear in the upload section.")
    
    # ... (Configuration logic from the previous response goes here, using st.session_state.account_list)
    # The functions for adding and removing accounts are not repeated for brevity.

    current_list = st.session_state.account_list.copy()

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
    if current_list:
        cols_config = st.columns(3)
        for i, account in enumerate(current_list):
            with cols_config[i % 3]:
                if st.button(f"Remove {account}", key=f"remove_{account}"):
                    st.session_state.account_list.remove(account)
                    st.experimental_rerun() 
    else:
        st.info("No accounts configured yet.")

    st.markdown("---")
    st.info(f"**Current number of configured accounts:** {len(st.session_state.account_list)}")
