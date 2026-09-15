| Source | Relationship | Target |
|---|---|---|
| 🧍 Guest | Association | Register |
| 🧍 Guest | Association | Login |
| 🧍 Guest | Association | Search Accommodations |
| 🧑‍💼 Registered User | Association | Manage Profile |
| 🧑‍💼 Registered User | Association | View Favorite Accommodations |
| 🧑‍💼 Registered User | Association | View Search History |
| 🧑‍💼 Registered User | Association | View Recently Viewed Accommodations |
| 🧑‍💼 Registered User | Association | View Personalized Recommendations |
| 🧑‍💼 Registered User | Association | Logout |
| 🛠️ Administrator | Association | Login |
| 🛠️ Administrator | Association | Access Administrator Dashboard |
| 🛠️ Administrator | Association | Manage Accommodations |
| 🛠️ Administrator | Association | Manage Accommodation Types |
| 🛠️ Administrator | Association | Manage Room Types |
| 🛠️ Administrator | Association | Manage Amenities |
| 🛠️ Administrator | Association | Manage Accommodation Images |
| 🛠️ Administrator | Association | Manage Room Images |
| 🛠️ Administrator | Association | Manage Locations and Coordinates |
| 🛠️ Administrator | Association | Manage Nearby Places |
| 🛠️ Administrator | Association | Manage Accommodation Sources |
| 🛠️ Administrator | Association | Verify Accommodation Information |
| 🛠️ Administrator | Association | Manage Users |
| 🛠️ Administrator | Association | Manage User Roles |
| 🛠️ Administrator | Association | Update Semantic Search Data |
| 🛠️ Administrator | Association | Logout |
| 🗺️ Google Maps Service | Association | Use Current Location |
| 🗺️ Google Maps Service | Association | View Accommodation on Map |
| 🗺️ Google Maps Service | Association | Manage Locations and Coordinates |
| 🗺️ Google Maps Service | Association | View Nearby Places |
| 🧑‍💼 Registered User | Generalization | 🧍 Guest |
| Search Accommodations | «include» | Enter Natural-Language Query |
| Search Accommodations | «include» | Process Search Query |
| Search Accommodations | «include» | Semantic Search |
| Search Accommodations | «include» | View Search Results |
| Process Search Query | «include» | Preprocess Query |
| Semantic Search | «include» | Convert Query to Vector |
| Semantic Search | «include» | Retrieve Accommodation Vectors |
| Semantic Search | «include» | Calculate Semantic Similarity |
| Semantic Search | «include» | Apply Search Conditions |
| Semantic Search | «include» | Rank Search Results |
| Manage Profile | «include» | Authenticate User |
| Add Accommodation to Favorites | «include» | Authenticate User |
| View Favorite Accommodations | «include» | Authenticate User |
| Remove Accommodation from Favorites | «include» | Authenticate User |
| View Search History | «include» | Authenticate User |
| View Recently Viewed Accommodations | «include» | Authenticate User |
| Compare Accommodations | «include» | Authenticate User |
| View Personalized Recommendations | «include» | Authenticate User |
| Compare Accommodations | «include» | Select Accommodations |
| Compare Accommodations | «include» | Display Comparison Results |
| View Personalized Recommendations | «include» | Retrieve User Preferences |
| View Personalized Recommendations | «include» | Retrieve Favorites and Search History |
| View Personalized Recommendations | «include» | Generate Recommendations |
| View Personalized Recommendations | «include» | Display Recommended Accommodations |
| Access Administrator Dashboard | «include» | Authenticate Administrator |
| Manage Accommodations | «include» | Authenticate Administrator |
| Manage Users | «include» | Authenticate Administrator |
| Manage User Roles | «include» | Authenticate Administrator |
| Add Accommodation | «include» | Validate Accommodation Information |
| Edit Accommodation | «include» | Validate Accommodation Information |
| Add Accommodation | «include» | Record Data Source |
| Edit Accommodation | «include» | Record Verification Date |
| Add Accommodation | «include» | Update Semantic Search Data |
| Edit Accommodation | «include» | Update Semantic Search Data |
| Delete or Unpublish Accommodation | «include» | Update Semantic Search Data |
| Manage Accommodation Images | «include» | Upload Accommodation Images |
| Manage Accommodation Images | «include» | Preview Images |
| Manage Room Images | «include» | Upload Room Images |
| Manage Room Images | «include» | Preview Room Images |
| Manage Nearby Places | «include» | Manage Place Information |
| Manage Nearby Places | «include» | Manage Accommodation-Place Distance |
| Manage Accommodation Sources | «include» | Record Source URL |
| Manage Accommodation Sources | «include» | Record Verification Date |
| Manage Accommodation Sources | «include» | Verify Accommodation Information |
| Manage User Roles | «include» | Authorize User Access |
| Update Semantic Search Data | «include» | Prepare Accommodation Text |
| Update Semantic Search Data | «include» | Convert Accommodation Data to Vector |
| Update Semantic Search Data | «include» | Save or Update Accommodation Vector |
| Select Accommodation Type | «extend» | Search Accommodations |
| Select District | «extend» | Search Accommodations |
| Apply Search Filters | «extend» | Search Accommodations |
| Use Current Location | «extend» | Search Accommodations |
| Record Search History | «extend» | Search Accommodations |
| View Accommodation Details | «extend» | View Search Results |
| View Accommodation on Map | «extend» | View Accommodation Details |
| View Nearby Places | «extend» | View Accommodation Details |
| Share Accommodation | «extend» | View Accommodation Details |
| Add Accommodation to Favorites | «extend» | View Accommodation Details |
| Record Recently Viewed | «extend» | View Accommodation Details |
| Remove Accommodation from Favorites | «extend» | View Favorite Accommodations |
| Compare Accommodations | «extend» | View Search Results |
| Add Accommodation | «extend» | Manage Accommodations |
| View Accommodation Information | «extend» | Manage Accommodations |
| Edit Accommodation | «extend» | Manage Accommodations |
| Delete or Unpublish Accommodation | «extend» | Manage Accommodations |
| Set Cover Image | «extend» | Manage Accommodation Images |
| Reorder Images | «extend» | Manage Accommodation Images |
| Delete Image | «extend» | Manage Accommodation Images |
| Set Room Cover Image | «extend» | Manage Room Images |
| Reorder Room Images | «extend» | Manage Room Images |
| Delete Room Image | «extend» | Manage Room Images |
| View User Information | «extend» | Manage Users |
| Edit User Information | «extend» | Manage Users |
| Disable User Account | «extend» | Manage Users |
| Disable Accommodation Vector | «extend» | Update Semantic Search Data |
