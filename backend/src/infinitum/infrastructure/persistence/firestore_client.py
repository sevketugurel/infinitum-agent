# File: src/infinitum/db/firestore_client.py
import firebase_admin
from firebase_admin import credentials, firestore
from infinitum.settings import settings
import uuid
from datetime import datetime

# Initialize Firebase Admin SDK (do this once in your main.py)
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {'projectId': settings.FIREBASE_PROJECT_ID})

db = firestore.client()

def save_product_snapshot(product_data: dict):
    """Saves a product data dictionary to the 'products' collection."""
    try:
        # Generate a unique document ID
        doc_id = None
        
        # Try to use title as base for document ID
        if product_data.get('title'):
            # Clean the title to make a valid document ID
            title = product_data['title']
            doc_id = title.replace(' ', '_').replace('-', '_')[:50]  # Limit length
            doc_id = ''.join(c for c in doc_id if c.isalnum() or c == '_')  # Keep only alphanumeric and underscore
        
        # Fallback to URL-based ID
        if not doc_id and product_data.get('url'):
            url = product_data['url']
            if '/dp/' in url:  # Amazon product ID
                doc_id = url.split('/dp/')[1].split('/')[0]
        
        # Final fallback: random UUID
        if not doc_id:
            doc_id = str(uuid.uuid4())[:8]
        
        # Add timestamp to make it unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_id = f"{doc_id}_{timestamp}"
        
        # Add metadata
        product_data['saved_at'] = datetime.now().isoformat()
        product_data['document_id'] = doc_id
        
        # Save to Firestore
        products_ref = db.collection('products')
        products_ref.document(doc_id).set(product_data, merge=True)
        
        print(f"Successfully saved product to Firestore with ID: {doc_id}")
        return doc_id
        
    except Exception as e:
        print(f"Error saving to Firestore: {str(e)}")
        return None