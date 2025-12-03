# Design Document: Backend API Completion

## Overview

This design document outlines the architecture and implementation approach for completing the AlphaLab backend. The design follows the existing FastAPI patterns and integrates seamlessly with the current codebase structure.

### Design Principles

1. **Consistency**: Follow existing code patterns (router structure, service layer, Pydantic schemas)
2. **Modularity**: Each feature is self-contained with clear boundaries
3. **Testability**: Services are dependency-injected and easily mockable
4. **Performance**: Use async/await throughout, implement caching where appropriate
5. **Security**: Validate all inputs, require authentication except for public endpoints

## Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ API Routers  │  │   Services   │  │   Models     │     │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤     │
│  │ certificates │  │ certificate  │  │ Certificate  │     │
│  │ notifications│  │ notification │  │ Notification │     │
│  │ dashboard    │  │ dashboard    │  │ ActivityLog  │     │
│  │ export       │  │ export       │  │ Export       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
│                    ┌───────▼────────┐                       │
│                    │   Database     │                       │
│                    │  (Supabase)    │                       │
│                    └────────────────┘                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Certificate Service

**Purpose**: Handle certificate generation, storage, and verification

**Class Structure**:
```python
class CertificateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pdf_generator = PDFGenerator()
        self.storage = StorageClient()
    
    async def generate_certificate(
        self, 
        user_id: UUID, 
        result_id: UUID
    ) -> Certificate:
        """Generate certificate for a test result"""
        
    async def get_certificate(
        self, 
        certificate_id: UUID, 
        user_id: UUID
    ) -> Certificate:
        """Get certificate by ID"""
        
    async def verify_certificate(
        self, 
        verification_code: str
    ) -> dict:
        """Public verification of certificate"""
        
    async def generate_pdf(
        self, 
        certificate: Certificate
    ) -> bytes:
        """Generate PDF document"""
```

**Key Methods**:

1. `generate_certificate()`:
   - Validate result exists and is profitable
   - Generate unique verification code (format: ALX-YYYY-MMDD-XXXXX)
   - Create certificate record in database
   - Generate PDF using ReportLab
   - Upload PDF to storage (Supabase Storage)
   - Return certificate with URLs

2. `verify_certificate()`:
   - Look up certificate by verification code
   - Increment view count
   - Return public certificate data (no sensitive info)

3. `generate_pdf()`:
   - Use ReportLab to create styled PDF
   - Include: Agent name, metrics, QR code, verification code
   - Return PDF as bytes

**Database Operations**:
- INSERT into certificates table
- SELECT from certificates with verification_code
- UPDATE view_count
- JOIN with test_results for metrics

### 2. Notification Service

**Purpose**: Manage user notifications

**Class Structure**:
```python
class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_notification(
        self,
        user_id: UUID,
        type: str,
        category: str,
        title: str,
        message: str,
        **kwargs
    ) -> Notification:
        """Create a new notification"""
        
    async def list_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0
    ) -> List[Notification]:
        """List user notifications"""
        
    async def get_unread_count(
        self,
        user_id: UUID
    ) -> int:
        """Get count of unread notifications"""
        
    async def mark_as_read(
        self,
        notification_id: UUID,
        user_id: UUID
    ) -> Notification:
        """Mark notification as read"""
        
    async def mark_all_read(
        self,
        user_id: UUID
    ) -> int:
        """Mark all notifications as read"""
        
    async def clear_all(
        self,
        user_id: UUID
    ) -> int:
        """Delete all notifications"""
```

**Key Methods**:

1. `create_notification()`:
   - Validate notification type and category
   - Insert into notifications table
   - Return created notification

2. `list_notifications()`:
   - Query with filters (unread_only)
   - Order by created_at DESC
   - Apply pagination
   - Return list of notifications

3. `mark_as_read()`:
   - Verify ownership
   - Update is_read = true, read_at = now()
   - Return updated notification

**Database Operations**:
- INSERT into notifications
- SELECT with WHERE user_id and optional is_read filter
- UPDATE is_read and read_at
- DELETE WHERE user_id

### 3. Dashboard Service

**Purpose**: Aggregate statistics and activity for dashboard

**Class Structure**:
```python
class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_stats(
        self,
        user_id: UUID
    ) -> dict:
        """Get dashboard overview statistics"""
        
    async def get_activity(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[dict]:
        """Get recent activity feed"""
        
    async def get_quick_start_progress(
        self,
        user_id: UUID
    ) -> dict:
        """Get onboarding progress"""
```

**Key Methods**:

1. `get_stats()`:
   - Count total agents (not archived)
   - Count total tests run
   - Get best PnL from test_results
   - Calculate average win rate
   - Calculate trends (compare to previous period)
   - Identify best performing agent
   - Return aggregated stats

2. `get_activity()`:
   - Query activity_log table
   - Order by created_at DESC
   - Limit results
   - Return formatted activity items

3. `get_quick_start_progress()`:
   - Check if user has created agent
   - Check if user has run backtest
   - Check if user has generated certificate
   - Calculate progress percentage
   - Return steps with completion status

**Database Operations**:
- COUNT queries on agents, test_results
- MAX, AVG aggregations on test_results
- SELECT from activity_log with ORDER BY and LIMIT
- Multiple EXISTS checks for onboarding steps

### 4. Export Service

**Purpose**: Generate data export packages

**Class Structure**:
```python
class ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = StorageClient()
    
    async def create_export(
        self,
        user_id: UUID,
        include: dict
    ) -> dict:
        """Create export job"""
        
    async def get_export_status(
        self,
        export_id: UUID,
        user_id: UUID
    ) -> dict:
        """Get export job status"""
        
    async def generate_export_package(
        self,
        export_id: UUID
    ) -> None:
        """Background task to generate export"""
```

**Key Methods**:

1. `create_export()`:
   - Create export job record with status "processing"
   - Queue background task for generation
   - Return export_id and status

2. `generate_export_package()`:
   - Query all requested data (agents, results, trades, etc.)
   - Format as JSON
   - Create ZIP archive if requested
   - Upload to storage
   - Update export record with download_url and status "ready"

3. `get_export_status()`:
   - Query export record
   - Return status, progress, download_url

**Database Operations**:
- INSERT into exports table (new table needed)
- SELECT from agents, test_results, trades, user_settings
- UPDATE export status and download_url

### 5. PDF Generator Utility

**Purpose**: Generate styled PDF certificates

**Class Structure**:
```python
class PDFGenerator:
    def generate_certificate(
        self,
        certificate: Certificate,
        result: TestResult
    ) -> bytes:
        """Generate certificate PDF"""
```

**Implementation Details**:
- Use ReportLab library
- A4 page size
- Dark theme (#0A0A0F background)
- Cyan accent color (#00D4FF)
- Include:
  - AlphaLab logo/title
  - Agent name (large, centered)
  - Key metrics table (PnL, win rate, trades, etc.)
  - QR code (bottom right)
  - Verification code (bottom left)
  - Test period and duration

**Styling**:
```python
# Colors
BACKGROUND = HexColor("#0A0A0F")
ACCENT = HexColor("#00D4FF")
TEXT_PRIMARY = HexColor("#FFFFFF")
TEXT_SECONDARY = HexColor("#A1A1AA")

# Fonts
TITLE_FONT = ("Helvetica-Bold", 24)
AGENT_FONT = ("Helvetica-Bold", 32)
BODY_FONT = ("Helvetica", 14)
SMALL_FONT = ("Helvetica", 10)
```

## Data Models

### Certificate Schema (Pydantic)

```python
class CertificateCreate(BaseModel):
    result_id: UUID
    include_reasoning_trace: bool = False

class CertificateResponse(BaseModel):
    id: UUID
    verification_code: str
    share_url: str
    pdf_url: str
    image_url: Optional[str]
    issued_at: datetime
    view_count: int
    
    class Config:
        from_attributes = True

class CertificateVerifyResponse(BaseModel):
    verified: bool
    certificate: Optional[dict]
```

### Notification Schema (Pydantic)

```python
class NotificationResponse(BaseModel):
    id: UUID
    type: str
    category: str
    title: str
    message: str
    action_url: Optional[str]
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
```

### Dashboard Schema (Pydantic)

```python
class DashboardStatsResponse(BaseModel):
    total_agents: int
    tests_run: int
    best_pnl: Optional[float]
    avg_win_rate: Optional[float]
    trends: dict
    best_agent: Optional[dict]

class ActivityItem(BaseModel):
    id: UUID
    type: str
    agent_name: Optional[str]
    description: str
    pnl: Optional[float]
    result_id: Optional[UUID]
    timestamp: datetime

class ActivityResponse(BaseModel):
    activity: List[ActivityItem]

class QuickStartStep(BaseModel):
    id: str
    label: str
    description: str
    is_complete: bool
    href: str
    cta_text: str

class QuickStartResponse(BaseModel):
    steps: List[QuickStartStep]
    progress_pct: float
```

### Export Schema (Pydantic)

```python
class ExportCreate(BaseModel):
    include: dict
    format: str = "zip"

class ExportResponse(BaseModel):
    export_id: UUID
    status: str
    progress_pct: Optional[float]
    download_url: Optional[str]
    expires_at: Optional[datetime]
    size_mb: Optional[float]
```

## Error Handling

### Custom Exceptions

```python
class CertificateError(Exception):
    """Base exception for certificate operations"""

class UnprofitableResultError(CertificateError):
    """Result is not profitable, cannot generate certificate"""

class CertificateNotFoundError(CertificateError):
    """Certificate not found"""

class ExportError(Exception):
    """Base exception for export operations"""
```

### Error Response Format

All errors return consistent JSON:
```json
{
  "detail": "Human readable message",
  "error_code": "ERROR_CODE",
  "status_code": 400
}
```

## Testing Strategy

### Unit Tests

1. **Service Tests**:
   - Mock database session
   - Test each service method independently
   - Verify correct SQL queries
   - Test error conditions

2. **PDF Generator Tests**:
   - Test PDF generation with sample data
   - Verify PDF structure
   - Test QR code generation

### Integration Tests

1. **API Endpoint Tests**:
   - Test full request/response cycle
   - Mock authentication
   - Verify status codes
   - Validate response schemas

2. **Database Tests**:
   - Use test database
   - Test CRUD operations
   - Verify constraints and indexes

### Test Coverage Goals

- Services: 90%+ coverage
- API routes: 85%+ coverage
- Utilities: 80%+ coverage

## Security Considerations

1. **Authentication**:
   - All endpoints require JWT except public verification
   - Verify user ownership of resources

2. **Input Validation**:
   - Use Pydantic schemas for all inputs
   - Validate UUIDs, enums, ranges

3. **Rate Limiting**:
   - Implement rate limiting on certificate generation (max 10/hour)
   - Rate limit export generation (max 5/day)

4. **Data Access**:
   - Always filter by user_id
   - Use parameterized queries (SQLAlchemy handles this)

## Performance Optimizations

1. **Caching**:
   - Cache dashboard stats for 5 minutes
   - Cache activity feed for 1 minute

2. **Database Indexes**:
   - Ensure indexes on user_id columns
   - Index on verification_code for certificates
   - Index on created_at for activity_log

3. **Async Operations**:
   - Use async/await throughout
   - Background tasks for PDF generation and exports

4. **Pagination**:
   - Implement pagination for all list endpoints
   - Default limit: 20, max limit: 100

## Deployment Considerations

1. **Environment Variables**:
   - STORAGE_BUCKET: Supabase storage bucket name
   - CERTIFICATE_BASE_URL: Base URL for certificate sharing
   - EXPORT_EXPIRY_HOURS: Export download link expiry (default: 24)

2. **Storage Setup**:
   - Create "certificates" bucket in Supabase Storage
   - Create "exports" bucket in Supabase Storage
   - Set appropriate CORS and access policies

3. **Background Tasks**:
   - Use FastAPI BackgroundTasks for PDF generation
   - Consider Celery for export generation if needed

## Migration Plan

1. **Phase 1**: Service Layer
   - Implement CertificateService
   - Implement NotificationService
   - Implement DashboardService
   - Implement ExportService

2. **Phase 2**: API Routes
   - Create certificates.py router
   - Create notifications.py router
   - Create dashboard.py router
   - Create export.py router

3. **Phase 3**: Utilities
   - Implement PDFGenerator
   - Implement storage helpers

4. **Phase 4**: Integration
   - Register routers in app.py
   - Register WebSocket handlers
   - Add error handlers

5. **Phase 5**: Testing
   - Write unit tests
   - Write integration tests
   - Manual testing with frontend

## Dependencies

New Python packages needed:
```
reportlab==4.0.8      # PDF generation
qrcode==7.4.2         # QR code generation
Pillow==10.2.0        # Image processing for QR codes
```

All other dependencies are already in requirements.txt.
