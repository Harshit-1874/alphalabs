# Implementation Plan: Backend API Completion

## Task Overview

This implementation plan breaks down the backend completion into discrete, manageable coding tasks. Each task builds incrementally on previous work, ensuring no orphaned code.

---

## Phase 1: Foundation - Service Layer

- [x] 1. Create Certificate Service
  - Create `backend/services/certificate_service.py` with CertificateService class
  - Implement `generate_certificate()` method with verification code generation
  - Implement `get_certificate()` method with user ownership validation
  - Implement `verify_certificate()` method for public verification
  - Implement `_generate_verification_code()` helper method
  - _Requirements: 1.1, 1.4_

- [x] 2. Create Notification Service
  - Create `backend/services/notification_service.py` with NotificationService class
  - Implement `create_notification()` method
  - Implement `list_notifications()` method with pagination
  - Implement `get_unread_count()` method
  - Implement `mark_as_read()` method
  - Implement `mark_all_read()` method
  - Implement `clear_all()` method
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. Create Dashboard Service
  - Create `backend/services/dashboard_service.py` with DashboardService class
  - Implement `get_stats()` method with aggregation queries
  - Implement `_calculate_trends()` helper method
  - Implement `get_activity()` method querying activity_log
  - Implement `get_quick_start_progress()` method
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Create Export Service
  - Create `backend/services/export_service.py` with ExportService class
  - Implement `create_export()` method
  - Implement `get_export_status()` method
  - Implement `generate_export_package()` background task method
  - Implement `_collect_user_data()` helper method
  - Implement `_create_zip_archive()` helper method
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

---

## Phase 2: Utilities and Helpers

- [x] 5. Create PDF Generator Utility
  - Create `backend/utils/pdf_generator.py` with PDFGenerator class
  - Implement `generate_certificate()` method using ReportLab
  - Implement `_draw_background()` helper method
  - Implement `_draw_header()` helper method
  - Implement `_draw_metrics_table()` helper method
  - Implement `_generate_qr_code()` helper method
  - Implement `_draw_footer()` helper method
  - _Requirements: 1.2, 7.5_

- [x] 6. Create Storage Helper
  - Create `backend/utils/storage.py` with StorageClient class
  - Implement `upload_file()` method for Supabase Storage
  - Implement `get_public_url()` method
  - Implement `delete_file()` method
  - _Requirements: 1.2_

- [x] 7. Create Verification Code Generator
  - Create `backend/utils/verification_code.py`
  - Implement `generate_verification_code()` function (format: ALX-YYYY-MMDD-XXXXX)
  - Implement `validate_verification_code()` function
  - _Requirements: 1.1_

---

## Phase 3: Pydantic Schemas

- [x] 8. Create Certificate Schemas
  - Create `backend/schemas/certificate_schemas.py`
  - Define `CertificateCreate` schema
  - Define `CertificateResponse` schema
  - Define `CertificateVerifyResponse` schema
  - _Requirements: 1.1, 1.4, 8.1_

- [x] 9. Create Notification Schemas
  - Create `backend/schemas/notification_schemas.py`
  - Define `NotificationResponse` schema
  - Define `NotificationListResponse` schema
  - Define `UnreadCountResponse` schema
  - _Requirements: 2.1, 2.2, 8.1_

- [x] 10. Create Dashboard Schemas
  - Create `backend/schemas/dashboard_schemas.py`
  - Define `DashboardStatsResponse` schema
  - Define `ActivityItem` schema
  - Define `ActivityResponse` schema
  - Define `QuickStartStep` schema
  - Define `QuickStartResponse` schema
  - _Requirements: 3.1, 3.5, 8.1_

- [x] 11. Create Export Schemas
  - Create `backend/schemas/export_schemas.py`
  - Define `ExportCreate` schema
  - Define `ExportResponse` schema
  - _Requirements: 4.1, 4.2, 8.1_

---

## Phase 4: API Routes - Certificates

- [x] 12. Create Certificates Router
  - Create `backend/api/certificates.py` with APIRouter
  - Implement `POST /api/certificates` endpoint
  - Implement `GET /api/certificates/{id}` endpoint
  - Implement `GET /api/certificates/{id}/pdf` endpoint for file download
  - Implement `GET /api/certificates/verify/{code}` endpoint (no auth required)
  - Add proper error handling and validation
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 8.2, 8.3_

---

## Phase 5: API Routes - Notifications

- [x] 13. Create Notifications Router
  - Create `backend/api/notifications.py` with APIRouter
  - Implement `GET /api/notifications` endpoint with query params
  - Implement `GET /api/notifications/unread-count` endpoint
  - Implement `POST /api/notifications/{id}/read` endpoint
  - Implement `POST /api/notifications/mark-all-read` endpoint
  - Implement `DELETE /api/notifications/clear` endpoint
  - Add proper error handling and validation
  - _Requirements: 6.5, 6.6, 6.7, 6.8, 6.9, 8.2, 8.3_

---

## Phase 6: API Routes - Dashboard

- [x] 14. Create Dashboard Router
  - Create `backend/api/dashboard.py` with APIRouter
  - Implement `GET /api/dashboard/stats` endpoint
  - Implement `GET /api/dashboard/activity` endpoint with limit param
  - Implement `GET /api/dashboard/quick-start` endpoint
  - Add proper error handling and validation
  - _Requirements: 6.10, 6.11, 6.12, 8.2, 8.3_

---

## Phase 7: API Routes - Export

- [x] 15. Create Export Router
  - Create `backend/api/export.py` with APIRouter
  - Implement `POST /api/export` endpoint
  - Implement `GET /api/export/{id}` endpoint
  - Add proper error handling and validation
  - _Requirements: 6.13, 6.14, 8.2, 8.3_

---

## Phase 8: Database Models (if needed)

- [x] 16. Add Export Model (if not exists)
  - Check if Export model exists in `backend/models/`
  - If not, create Export model with fields: id, user_id, status, progress_pct, download_url, expires_at, created_at
  - Add relationship to User model
  - _Requirements: 4.2, 9.1_

---

## Phase 9: Application Integration

- [x] 17. Register New Routers in Main App
  - Update `backend/app.py` to import new routers
  - Add `app.include_router(certificates.router)`
  - Add `app.include_router(notifications.router)`
  - Add `app.include_router(dashboard.router)`
  - Add `app.include_router(export.router)`
  - _Requirements: 6.1-6.14_

- [x] 18. Register WebSocket Handlers
  - Update `backend/app.py` to import websocket handlers
  - Add WebSocket route for `/ws/backtest/{session_id}`
  - Add WebSocket route for `/ws/forward/{session_id}`
  - Ensure JWT authentication is applied to WebSocket connections
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 19. Add Global Error Handlers
  - Create `backend/error_handlers.py` if not exists
  - Add exception handler for CertificateError
  - Add exception handler for ExportError
  - Register error handlers in app.py
  - _Requirements: 8.1, 8.2_

---

## Phase 10: Storage Setup

- [ ] 20. Configure Supabase Storage
  - Document storage bucket creation steps
  - Create "certificates" bucket in Supabase
  - Create "exports" bucket in Supabase
  - Set public access policy for certificates
  - Set private access policy for exports
  - _Requirements: 1.2, 4.3_

---

## Phase 11: Testing

- [ ]* 21. Write Service Unit Tests
  - Create `backend/tests/test_certificate_service.py`
  - Create `backend/tests/test_notification_service.py`
  - Create `backend/tests/test_dashboard_service.py`
  - Create `backend/tests/test_export_service.py`
  - Mock database sessions and test all service methods
  - _Requirements: 10.1, 10.2_

- [ ]* 22. Write API Integration Tests
  - Create `backend/tests/test_certificates_api.py`
  - Create `backend/tests/test_notifications_api.py`
  - Create `backend/tests/test_dashboard_api.py`
  - Create `backend/tests/test_export_api.py`
  - Test full request/response cycles with mocked auth
  - _Requirements: 10.3, 10.4, 10.5_

- [ ]* 23. Write PDF Generator Tests
  - Create `backend/tests/test_pdf_generator.py`
  - Test PDF generation with sample certificate data
  - Verify PDF structure and content
  - Test QR code generation
  - _Requirements: 10.1_

---

## Phase 12: Documentation and Deployment

- [x] 24. Update Requirements.txt
  - Add reportlab==4.0.8
  - Add qrcode==7.4.2
  - Add Pillow==10.2.0
  - _Requirements: 7.5_

- [ ] 25. Update Environment Variables Documentation
  - Document STORAGE_BUCKET variable
  - Document CERTIFICATE_BASE_URL variable
  - Document EXPORT_EXPIRY_HOURS variable
  - Update .env.example file
  - _Requirements: 1.2, 4.3_

- [ ] 26. Create Migration Scripts (if needed)
  - Check if exports table needs to be created
  - Create SQL migration file if needed
  - Update migration runner
  - _Requirements: 9.1_

---

## Implementation Notes

- **Order**: Tasks should be completed in order as each phase builds on the previous
- **Testing**: Optional test tasks (marked with *) can be skipped for faster MVP
- **Dependencies**: Ensure all Phase 1-3 tasks are complete before starting Phase 4
- **Integration**: Phase 9 ties everything together - complete all previous phases first
- **Validation**: After each phase, verify the code compiles and basic functionality works

## Success Criteria

- All API endpoints from the specification are implemented and functional
- Services handle business logic correctly with proper error handling
- PDF generation produces valid, styled certificates
- WebSocket handlers are registered and streaming events
- All database operations work correctly
- Frontend can successfully call all new endpoints
