# Requirements Document: Backend API Completion

## Introduction

This document outlines the requirements for completing the AlphaLab backend implementation. After analyzing the backend specification documents and the current implementation, several critical API endpoints and features are missing that are required for the frontend to function properly.

## Glossary

- **System**: The AlphaLab backend FastAPI application
- **Certificate**: A shareable PDF document proving trading agent performance
- **Notification**: An in-app alert message for users about system events
- **Dashboard**: The main overview page showing user statistics and activity
- **Export**: A data package containing user's agents, results, and settings
- **Activity Log**: A chronological feed of user actions and test results
- **WebSocket Handler**: A real-time connection endpoint for streaming test data

## Requirements

### Requirement 1: Certificate Generation and Management

**User Story:** As a user, I want to generate shareable certificates for my profitable test results, so that I can prove my agent's performance to others.

#### Acceptance Criteria

1. WHEN a user requests certificate generation for a profitable result, THE System SHALL create a certificate record with a unique verification code
2. WHEN a certificate is generated, THE System SHALL produce a PDF document containing result metrics, agent details, and a QR code
3. WHEN a user requests certificate download, THE System SHALL return the PDF file
4. WHERE a verification code is provided, THE System SHALL allow public verification without authentication
5. WHEN a certificate is accessed via verification code, THE System SHALL increment the view count

### Requirement 2: Notification System

**User Story:** As a user, I want to receive notifications about important events, so that I stay informed about my tests and system updates.

#### Acceptance Criteria

1. THE System SHALL provide an endpoint to list user notifications with pagination
2. THE System SHALL provide an endpoint to retrieve unread notification count
3. WHEN a user marks a notification as read, THE System SHALL update the notification status and timestamp
4. THE System SHALL provide an endpoint to mark all notifications as read
5. THE System SHALL provide an endpoint to clear all notifications

### Requirement 3: Dashboard Statistics

**User Story:** As a user, I want to see an overview of my performance statistics on the dashboard, so that I can quickly assess my progress.

#### Acceptance Criteria

1. THE System SHALL provide aggregate statistics including total agents, tests run, best PnL, and average win rate
2. THE System SHALL calculate trend metrics comparing current period to previous period
3. THE System SHALL identify and return the best performing agent
4. THE System SHALL provide quick-start onboarding progress tracking
5. THE System SHALL return activity feed with recent user actions and test completions

### Requirement 4: Data Export

**User Story:** As a user, I want to export all my data, so that I have a backup and can analyze it externally.

#### Acceptance Criteria

1. WHEN a user requests data export, THE System SHALL create an export package containing agent configs, test results, trade history, and settings
2. THE System SHALL support both JSON and ZIP format exports
3. THE System SHALL track export job status with progress percentage
4. WHEN an export is ready, THE System SHALL provide a download URL with expiration time
5. THE System SHALL include optional reasoning traces in exports based on user preference

### Requirement 5: WebSocket Integration

**User Story:** As a user, I want real-time updates during backtests and forward tests, so that I can monitor progress without refreshing.

#### Acceptance Criteria

1. THE System SHALL register WebSocket handlers in the main application
2. WHEN a backtest session starts, THE System SHALL accept WebSocket connections at /ws/backtest/{session_id}
3. WHEN a forward test session starts, THE System SHALL accept WebSocket connections at /ws/forward/{session_id}
4. THE System SHALL verify JWT tokens for WebSocket authentication
5. THE System SHALL broadcast session events to all connected clients for a session

### Requirement 6: Missing API Endpoints

**User Story:** As a frontend developer, I want all specified API endpoints to be implemented, so that the UI can function completely.

#### Acceptance Criteria

1. THE System SHALL implement POST /api/certificates endpoint for certificate generation
2. THE System SHALL implement GET /api/certificates/{id} endpoint for certificate retrieval
3. THE System SHALL implement GET /api/certificates/{id}/pdf endpoint for PDF download
4. THE System SHALL implement GET /api/certificates/verify/{code} endpoint for public verification
5. THE System SHALL implement GET /api/notifications endpoint with filtering
6. THE System SHALL implement GET /api/notifications/unread-count endpoint
7. THE System SHALL implement POST /api/notifications/{id}/read endpoint
8. THE System SHALL implement POST /api/notifications/mark-all-read endpoint
9. THE System SHALL implement DELETE /api/notifications/clear endpoint
10. THE System SHALL implement GET /api/dashboard/stats endpoint
11. THE System SHALL implement GET /api/dashboard/activity endpoint
12. THE System SHALL implement GET /api/dashboard/quick-start endpoint
13. THE System SHALL implement POST /api/export endpoint
14. THE System SHALL implement GET /api/export/{id} endpoint

### Requirement 7: Service Layer Implementation

**User Story:** As a developer, I want service classes to handle business logic, so that the code is maintainable and testable.

#### Acceptance Criteria

1. THE System SHALL implement CertificateService class with methods for generation, retrieval, and verification
2. THE System SHALL implement NotificationService class with methods for CRUD operations
3. THE System SHALL implement DashboardService class with methods for statistics aggregation
4. THE System SHALL implement ExportService class with methods for data packaging
5. THE System SHALL implement PDF generation utility using ReportLab

### Requirement 8: Error Handling and Validation

**User Story:** As a user, I want clear error messages when something goes wrong, so that I understand what happened and how to fix it.

#### Acceptance Criteria

1. WHEN a certificate generation fails, THE System SHALL return a descriptive error with error code
2. WHEN a user tries to generate a certificate for an unprofitable result, THE System SHALL return a validation error
3. WHEN a verification code is invalid, THE System SHALL return a 404 error
4. WHEN an export job fails, THE System SHALL update the status to "failed" with error details
5. THE System SHALL validate all request payloads using Pydantic schemas

### Requirement 9: Database Integration

**User Story:** As a system, I want to persist all data correctly, so that users don't lose their information.

#### Acceptance Criteria

1. THE System SHALL create certificate records in the certificates table
2. THE System SHALL create notification records in the notifications table
3. THE System SHALL query activity_log table for dashboard activity feed
4. THE System SHALL update notification read status and timestamps
5. THE System SHALL handle database errors gracefully with rollback

### Requirement 10: Testing Coverage

**User Story:** As a developer, I want comprehensive tests, so that I can confidently deploy changes.

#### Acceptance Criteria

1. THE System SHALL include unit tests for CertificateService
2. THE System SHALL include unit tests for NotificationService
3. THE System SHALL include integration tests for certificate API endpoints
4. THE System SHALL include integration tests for notification API endpoints
5. THE System SHALL include integration tests for dashboard API endpoints
