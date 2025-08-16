import streamlit as st
import pandas as pd
import os

# Set page configuration
st.set_page_config(
    page_title="Client Billing Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def main():
    # App selection interface
    st.title("Client Billing Applications")
    st.markdown("Choose which application to use:")
    
    app_choice = st.radio(
        "Select Application:",
        ["Standalone Sort Tool", "Client Sort Spreadsheet (Original)", "Advanced Billing Manager"],
        horizontal=True
    )
    
    if app_choice == "Standalone Sort Tool":
        try:
            from client_sort_standalone import main
            main()
        except ImportError as e:
            st.error(f"Error importing standalone tool: {e}")
        except Exception as e:
            st.error(f"Error running standalone tool: {e}")
    
    elif app_choice == "Client Sort Spreadsheet (Original)":
        try:
            from client_sort_spreadsheet import main
            main()
        except ImportError as e:
            st.error(f"Error importing spreadsheet tool: {e}")
        except Exception as e:
            st.error(f"Error running spreadsheet tool: {e}")
    
    elif app_choice == "Advanced Billing Manager":
        try:
            from simple_billing_workflow import main
            main()
        except ImportError as e:
            st.error(f"Error importing advanced billing: {e}")
        except Exception as e:
            st.error(f"Error running advanced billing: {e}")

if __name__ == "__main__":
    main()
