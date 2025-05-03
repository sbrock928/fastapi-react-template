# Adding a New Resource to Vibez

This document outlines the process for adding a new resource to the Vibez application, covering both backend and frontend implementation.

## Backend Implementation

### Step 1: Create the Model
Add your new model class to `app/resources/models.py`. Include both a base model for validation and a database model.

### Step 2: Create the DAO (Data Access Object)
Add a new DAO class to `app/resources/dao.py` that inherits from `GenericDAO` and implements any resource-specific data access methods.

### Step 3: Create the Service
Add a service class to `app/resources/service.py` that inherits from `GenericService` and implements business logic, validation, and custom operations.

### Step 4: Update Imports
Make sure all relevant files import your new models, DAOs, and services.

### Step 5: Register the Resource
Update `app/resources/registry.py` to register your new resource with the resource registry.

### Step 6: Add Custom Routes (Optional)
If needed, add custom routes to `app/resources/router.py` for resource-specific operations.

### Step 7: Update Database Initialization
Update `app/database.py` to import your new model for database table creation.

## Frontend Implementation

### Step 1: Update Resources.js Configuration
Add the new resource configuration to `app/static/js/resources.js` to define how it's displayed and edited in the UI.

### Step 2: Update the Resources Template
Modify `app/templates/resources.html` to include an option for the new resource type.

### Step 3: Update Backend Routes
Update relevant routes in `app/__init__.py` to include your new resource data.

### Step 4: Update Form Generation
If your resource uses new field types, update the form generation code in `app/static/js/resources.js`.

### Step 5: Update JavaScript Initialization
Update the JavaScript initialization in the templates to include your new resource data.

## Testing
After implementing all changes, test all CRUD operations for your new resource and any custom functionality.
