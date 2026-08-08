NOVA TECH STORE - DYNAMIC FULL STACK STORE
===========================================

Nova Tech Store is a real local full-stack store connected to the included
Python backend and JSON persistence. It does not use frontend-only mock data.

READY TEST LOGINS
-----------------
User 1: user@store.com / test1234
User 2: maramanwar1026@gmail.com / 123456789
User 3: shimaauni422@gmail.com / 1234567
Admin : admin@gmail.com / 1234567

See TEST_ACCOUNTS.txt for balances and details.
Change/remove test credentials before public deployment.

DYNAMIC STORE FEATURES
----------------------
- 30 seeded products across 14 categories
- Local/offline product artwork for every seeded product
- Live product count, category count and inventory units
- Rotating featured product spotlight
- Dynamic category chips with per-category counts
- Search across name, category, brand, badge and description
- Sort by featured, price, rating, stock or name
- In-stock-only filtering
- Product quick-view modal with live stock and quantity selector
- Product brand, description, rating, badge and stock meter
- Responsive animations, hover effects and catalog transitions
- User wallet and cart badge refresh from backend data

REAL BACKEND FLOWS
------------------
- User login using users.json + SHA-256 password verification
- User registration with real Gmail OTP
- Server-side cart stored in carts.json
- Products/stock/metadata stored in products.json
- Wallet balance stored with each user in users.json
- Checkout validates stock, deducts wallet, reduces stock and clears cart
- Profile username/password changes persist to JSON
- Admin login using admins.json
- Admin product CRUD with brand/description/rating/badge support
- Admin image upload/replacement
- Admin user list, filters and wallet charging
- Admin dashboard statistics, category overview and low-stock watch
- Backend JSON/Python files are blocked from direct browser access

REQUIREMENTS
------------
- Python 3
- Internet access only when sending registration OTP emails
- Gmail + Gmail App Password for real registration OTP
- No pip install is required

1) CONFIGURE REAL OTP EMAIL
---------------------------
The backend reads:
  NOVA_STORE_EMAIL
  NOVA_STORE_EMAIL_PASSWORD

Use a Gmail App Password, not the normal Gmail password.

Windows Command Prompt:
  setx NOVA_STORE_EMAIL "youraccount@gmail.com"
  setx NOVA_STORE_EMAIL_PASSWORD "your-16-character-app-password"

Close/reopen Command Prompt after setx.

macOS / Linux:
  export NOVA_STORE_EMAIL="youraccount@gmail.com"
  export NOVA_STORE_EMAIL_PASSWORD="your-16-character-app-password"

If Gmail is not configured, registration still works locally: the backend
prints the verification code in the Nova server window. If Gmail is configured,
the same backend sends the OTP by email. OTP values are never stored or exposed
as frontend demo data.

2) OPTIONAL: CREATE ANOTHER ADMIN
---------------------------------
A working admin account is already included for testing.
To create another admin:

Windows:
  Double-click setup_admin.bat

macOS / Linux:
  python3 setup_admin.py

3) RUN THE WEBSITE
------------------
IMPORTANT: Do not open index.html directly. The frontend needs the Python
backend process to read/write users.json, products.json and carts.json.

Windows:
  Double-click START_NOVA_STORE.bat
  (run.bat also forwards to the same launcher)

macOS / Linux:
  ./run.sh

Browser URL:
  http://127.0.0.1:5000

Keep the terminal open while using the site.

DATA STORAGE
------------
users.json       registered users + wallet balances
carts.json       user carts
products.json    products, stock, prices and display metadata
admins.json      admin accounts using password_hash
images/products/ local product images/artwork

MAIN FILES
----------
index.html          page structure
styles.css          responsive UI + store/admin animations
app.js              auth, dynamic catalog, cart, checkout, profile, admin
api_server.py       HTTP API + protected static server
user_manager.py     login, registration, OTP, users
admin_manager.py    admin authentication + legacy hash compatibility
product_manager.py  rich product persistence/search/statistics
product_service.py  product + image operations
cart_manager.py     cart persistence
cart_service.py     cart business logic
checkout_service.py stock + wallet checkout
wallet_manager.py   wallet operations
profile_manager.py  account operations
image_manager.py    product image storage

DEPLOYMENT NOTE
---------------
This project is suitable as a functional local/course project. JSON storage,
SHA-256-only passwords and in-memory tokens are intentionally simple and are
not a production authentication/database architecture for a public internet
store. For real public deployment use a database, salted password hashing
(e.g. Argon2/bcrypt), HTTPS, secure sessions/tokens, CSRF/CORS controls and a
production web server.

REAL PRODUCT PHOTOS (v5)
------------------------
- The 30 catalog products use curated real-world product/technology photography from Pexels.
- The primary photos load from the Pexels image CDN when internet access is available.
- The original local SVG images are retained as automatic fallbacks if a remote photo cannot load.
- See IMAGE_SOURCES.txt for the source page used for every product photo.
