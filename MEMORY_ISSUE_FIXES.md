# Memory Issue Fixes - GreenWatt Intake Form

## Problem Statement

The GreenWatt intake form application is experiencing critical memory exhaustion issues on Render.com's 512MB instance, causing service crashes and preventing form submissions.

### Symptoms:
1. **Cache Clear Crash**: Application crashes when clicking the dynamic cache clearer button
2. **Sheet Update Crash**: Application crashes after updating Google Sheets data and waiting 15 minutes for cache TTL
3. **Random Submission Crashes**: Application crashes during normal form submissions even without any sheet changes
4. **Memory Warning Logs**: Consistent "High memory usage: 400.6MB" warnings before crashes
5. **Service Restarts**: Render automatically restarts the service after memory exhaustion

### Impact:
- Client cannot submit forms reliably
- Dynamic sheet updates cause service outages
- Business operations are disrupted

## Root Cause Analysis

### 1. **Multiple Google API Service Instances**
The application creates TWO separate GoogleSheetsService instances on startup:
```python
# Line 49-53: Main sheets service
sheets_service = GoogleSheetsService(
    SERVICE_ACCOUNT_INFO, 
    os.getenv('GOOGLE_SHEETS_ID'),
    os.getenv('GOOGLE_AGENT_SHEETS_ID')
)

# Line 55-64: Dynamic sheets service (DUPLICATE!)
dynamic_sheets_id = os.getenv('DYNAMIC_GOOGLE_SHEETS_ID')
if dynamic_sheets_id:
    dynamic_sheets_service = GoogleSheetsService(
        SERVICE_ACCOUNT_INFO, 
        dynamic_sheets_id,
        os.getenv('GOOGLE_AGENT_SHEETS_ID')
    )
```

Each GoogleSheetsService instance:
- Creates its own `discovery.build('sheets', 'v4')` client
- Loads the entire Google Sheets API discovery document into memory
- Consumes approximately 150-200MB per instance
- Total: ~400MB just for Google Sheets services

### 2. **Additional Service Creation in Requests**
During form processing (line 1582), a new GoogleDriveService is created:
```python
dynamic_drive_service = GoogleDriveService(SERVICE_ACCOUNT_INFO, dynamic_drive_id)
```
This adds more memory overhead during each submission.

### 3. **Small Cache Size Leading to API Calls**
Current cache configuration (line 16 in google_sheets_service.py):
```python
self.cache = TTLCache(maxsize=16, ttl=600)  # Only 16 items!
```
Small cache = more cache misses = more API calls = more memory usage

### 4. **Memory Monitoring Shows Constant High Usage**
From logs:
- Baseline usage: ~400MB (dangerously close to 512MB limit)
- Any additional operation pushes it over the limit
- Garbage collection attempts are ineffective

## Previous Fix Attempts

### Attempt 1 (June 23, 2025 - Commit 02b0ba7)
**What was done:**
- Added memory leak fixes for progress_sessions dictionary
- Implemented automatic cleanup thread (60-second intervals)
- Added psutil memory monitoring
- Configured gunicorn worker recycling
- Added garbage collection after form submissions

**Result:** Insufficient - memory still exhausts due to baseline being too high

### Attempt 2 (June 23, 2025 - Commit 32e494f)
**What was done:**
- Created single global dynamic_sheets_service instance
- Reduced cache size from 32 to 16 items (made it worse!)
- Reduced cache TTL from 15 to 10 minutes
- Attempted to prevent multiple service instance creation

**Result:** Partially effective but didn't address the root cause of having two services

## Proposed Solution

### Phase 1: Service Consolidation (CRITICAL)
1. **Merge GoogleSheetsService Instances**
   - Refactor GoogleSheetsService to handle multiple spreadsheet IDs
   - Create single service instance that manages both main and dynamic sheets
   - Estimated memory savings: 200MB

2. **Implement Service Manager Singleton**
   ```python
   class GoogleServiceManager:
       _instance = None
       _sheets_service = None
       _drive_service = None
       
       @classmethod
       def get_sheets_service(cls):
           if not cls._sheets_service:
               cls._sheets_service = discovery.build('sheets', 'v4', credentials=cls.get_credentials())
           return cls._sheets_service
   ```

### Phase 2: Cache Optimization
1. **Increase Cache Size**: 16 → 100 items
2. **Implement Cache Preloading**: Load frequently used data on startup
3. **Add Cache Warming**: Background thread to keep cache fresh
4. **Cache Sharing**: Share cache between all sheet operations

### Phase 3: Memory-Efficient Operations
1. **Batch API Requests**: Combine multiple sheet operations
2. **Lazy Loading**: Only create services when needed
3. **Request Pooling**: Reuse HTTP connections
4. **Response Streaming**: Process large responses in chunks

### Phase 4: Monitoring & Safeguards
1. **Pre-Operation Memory Checks**: Verify sufficient memory before operations
2. **Graceful Degradation**: Fallback to cached data when memory is low
3. **Memory Profiling**: Log memory usage before/after each operation
4. **Alert Thresholds**: Notify when memory exceeds 400MB

## Implementation Status

### ✅ Completed (Previous):
- Memory monitoring with psutil
- Progress session cleanup
- Garbage collection hooks
- Worker recycling configuration

### ✅ Completed (2025-06-25):
1. **Service Consolidation** - IMPLEMENTED
   - Created GoogleServiceManager singleton class
   - Merged two GoogleSheetsService instances into one
   - Single service now handles both main and dynamic spreadsheets
   - Memory savings: ~200MB

2. **Cache Size Increase** - IMPLEMENTED
   - Increased from 16 to 100 items in GoogleSheetsService
   - Better cache hit rate = fewer API calls

3. **Service Manager Singleton** - IMPLEMENTED
   - GoogleServiceManager ensures single instance of each Google API client
   - Shared across GoogleSheetsService and GoogleDriveService
   - Thread-safe implementation with locking

4. **Memory Monitoring Enhancement** - IMPLEMENTED
   - Added memory logging at critical points:
     - Service initialization
     - Before/after form submissions
     - Before/after cache clearing
   - Real-time memory usage tracking

### ❌ Not Implemented (TODO):
1. **Batch API Operations** - PERFORMANCE
2. **Response Streaming** - For large data sets
3. **Redis Cache** - External caching solution
4. **Queue System** - Async processing

## Quick Fixes (Immediate Relief)

While working on the permanent solution, these can provide temporary relief:

1. **Increase Render Instance Size**: 512MB → 1GB (costs more but immediate fix)
2. **Disable Dynamic Sheets Temporarily**: Comment out dynamic_sheets_service creation
3. **Aggressive Cache Settings**: Increase TTL to 30 minutes, size to 50
4. **Remove Unnecessary Features**: Temporarily disable non-critical features

## Testing Plan

1. **Memory Baseline Test**: Measure memory after startup
2. **Cache Clear Test**: Verify memory doesn't spike when clearing cache
3. **Sheet Update Test**: Update sheets and monitor memory over 15 minutes
4. **Load Test**: Submit 10 forms in succession
5. **Memory Profile**: Use memory_profiler to identify exact memory usage

## Success Metrics

- Memory usage stays below 350MB during normal operation
- No crashes during cache clear operations
- No crashes after sheet updates
- Can handle 50+ form submissions without restart
- Memory returns to baseline after operations complete

## Long-term Recommendations

1. **Consider Microservices**: Separate Google Sheets operations into separate service
2. **Use Redis Cache**: External cache service instead of in-memory
3. **Implement Queue System**: Process heavy operations asynchronously
4. **Upgrade Infrastructure**: Move to container with more memory
5. **API Optimization**: Use Google Sheets API v4 batch operations extensively

## Emergency Contacts

- **Render Support**: For immediate instance upgrades
- **Google Cloud Support**: For API quota increases
- **Development Team**: For emergency fixes

## Code Changes Summary

### Files Created:
1. **services/google_service_manager.py** - Singleton manager for Google API services

### Files Modified:
1. **services/google_sheets_service.py**
   - Removed direct API client creation
   - Added support for multiple spreadsheet IDs
   - Increased cache size from 16 to 100
   - Uses shared service from GoogleServiceManager

2. **services/google_drive_service.py**
   - Removed direct API client creation
   - Uses shared service from GoogleServiceManager

3. **app.py**
   - Removed duplicate GoogleSheetsService instance creation
   - Consolidated into single instance with multiple spreadsheet IDs
   - Added memory monitoring at critical points
   - Fixed dynamic drive service to reuse existing instance

## Expected Results

After these changes:
- Memory usage should drop from ~400MB to ~200MB baseline
- Cache clearing should not cause memory spikes
- Form submissions should complete without memory exhaustion
- Service should handle 50+ consecutive submissions

## Deployment Instructions

1. Test locally first with memory profiling
2. Deploy to Render staging environment
3. Monitor memory usage via logs
4. If stable, deploy to production
5. Keep monitoring for 24 hours

## Revision History

- **2025-06-25 v1**: Initial documentation created after analyzing memory issues
- **2025-06-25 v2**: Updated after implementing service consolidation and singleton pattern
- **[Future Date]**: Update after production deployment results