import os
import time
import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
from shared.logging_config import get_logger
from shared.config import Config

# Module-level logger
logger = get_logger("database")

class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors"""
    pass

class DatabaseOperationError(Exception):
    """Custom exception for database operation errors"""
    pass

def get_db_connection(retry_count: int = 3, retry_delay: float = 1.0) -> psycopg2.extensions.connection:
    """
    Establish a new database connection with retry logic and structured logging.
    
    Args:
        retry_count: Number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Database connection object
        
    Raises:
        DatabaseConnectionError: If connection fails after all retries
    """
    db_config = Config.get_db_config()
    
    logger.debug("Attempting database connection", context={
        "host": db_config['host'],
        "port": db_config['port'],
        "dbname": db_config['dbname'],
        "user": db_config['user'],
        "retry_count": retry_count,
        "retry_delay": retry_delay
    })
    
    last_error = None
    
    for attempt in range(retry_count):
        start_time = time.time()
        
        try:
            conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                dbname=db_config['dbname'],
                user=db_config['user'],
                password=db_config['password'],
                connect_timeout=db_config['connect_timeout'],
                cursor_factory=DictCursor
            )
            
            connection_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            logger.info("Database connection established", context={
                "attempt": attempt + 1,
                "connection_time_ms": round(connection_time, 2),
                "host": db_config['host'],
                "dbname": db_config['dbname']
            })
            
            return conn
            
        except psycopg2.OperationalError as e:
            last_error = e
            connection_time = (time.time() - start_time) * 1000
            
            logger.warning("Database connection attempt failed", context={
                "attempt": attempt + 1,
                "max_attempts": retry_count,
                "connection_time_ms": round(connection_time, 2),
                "error": str(e),
                "host": db_config['host'],
                "dbname": db_config['dbname']
            })
            
            if attempt < retry_count - 1:
                logger.debug(f"Retrying database connection in {retry_delay} seconds")
                time.sleep(retry_delay)
            
        except Exception as e:
            last_error = e
            connection_time = (time.time() - start_time) * 1000
            
            logger.error("Unexpected error during database connection", 
                        error=e,
                        context={
                            "attempt": attempt + 1,
                            "connection_time_ms": round(connection_time, 2),
                            "host": db_config['host'],
                            "dbname": db_config['dbname']
                        })
            break
    
    # All attempts failed
    logger.error("Database connection failed after all retry attempts", 
                error=last_error,
                context={
                    "total_attempts": retry_count,
                    "retry_delay": retry_delay,
                    "host": db_config['host'],
                    "dbname": db_config['dbname']
                })
    
    raise DatabaseConnectionError(f"Failed to connect to database after {retry_count} attempts: {last_error}")

@contextmanager
def get_db_cursor(connection: Optional[psycopg2.extensions.connection] = None) -> Generator[psycopg2.extensions.cursor, None, None]:
    """
    Context manager for database cursor with automatic cleanup and logging.
    
    Args:
        connection: Existing connection to use, or None to create a new one
        
    Yields:
        Database cursor
    """
    conn = connection
    should_close_conn = False
    
    if conn is None:
        conn = get_db_connection()
        should_close_conn = True
    
    cursor = None
    start_time = time.time()
    
    try:
        cursor = conn.cursor()
        logger.debug("Database cursor created")
        
        yield cursor
        
        # Commit if no exception occurred
        conn.commit()
        
        operation_time = (time.time() - start_time) * 1000
        logger.debug("Database operation completed successfully", context={
            "operation_time_ms": round(operation_time, 2)
        })
        
    except Exception as e:
        # Rollback on error
        if conn:
            conn.rollback()
            
        operation_time = (time.time() - start_time) * 1000
        logger.error("Database operation failed, rolled back transaction", 
                    error=e,
                    context={
                        "operation_time_ms": round(operation_time, 2)
                    })
        raise DatabaseOperationError(f"Database operation failed: {e}") from e
        
    finally:
        if cursor:
            cursor.close()
            logger.debug("Database cursor closed")
            
        if should_close_conn and conn:
            conn.close()
            logger.debug("Database connection closed")

def execute_query(query: str, params: Optional[tuple] = None, 
                 fetch_one: bool = False, fetch_all: bool = False,
                 connection: Optional[psycopg2.extensions.connection] = None) -> Any:
    """
    Execute a database query with logging and error handling.
    
    Args:
        query: SQL query to execute
        params: Query parameters
        fetch_one: Whether to fetch one result
        fetch_all: Whether to fetch all results
        connection: Existing connection to use
        
    Returns:
        Query results or None
    """
    start_time = time.time()
    
    logger.debug("Executing database query", context={
        "query": query[:100] + "..." if len(query) > 100 else query,
        "params_count": len(params) if params else 0,
        "fetch_one": fetch_one,
        "fetch_all": fetch_all
    })
    
    try:
        with get_db_cursor(connection) as cursor:
            cursor.execute(query, params)
            
            result = None
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            
            execution_time = (time.time() - start_time) * 1000
            
            logger.info("Database query executed successfully", context={
                "execution_time_ms": round(execution_time, 2),
                "rows_affected": cursor.rowcount,
                "result_count": len(result) if result and isinstance(result, list) else (1 if result else 0)
            })
            
            return result
            
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        
        logger.error("Database query execution failed", 
                    error=e,
                    context={
                        "query": query[:100] + "..." if len(query) > 100 else query,
                        "params": params,
                        "execution_time_ms": round(execution_time, 2)
                    })
        raise

def check_database_health() -> Dict[str, Any]:
    """
    Check database health and return status information.
    
    Returns:
        Dictionary with health status information
    """
    start_time = time.time()
    
    try:
        with get_db_cursor() as cursor:
            # Test basic connectivity
            cursor.execute("SELECT 1 as health_check")
            result = cursor.fetchone()
            
            # Test database version
            cursor.execute("SELECT version()")
            version_result = cursor.fetchone()
            
            # Test table access (check if main tables exist)
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('files', 'processing_jobs', 'schedules')
            """)
            tables = cursor.fetchall()
            
            response_time = (time.time() - start_time) * 1000
            
            health_info = {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "database_version": version_result[0] if version_result else "unknown",
                "tables_found": len(tables),
                "expected_tables": 3
            }
            
            logger.debug("Database health check completed", context=health_info)
            
            return health_info
            
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        
        health_info = {
            "status": "unhealthy",
            "response_time_ms": round(response_time, 2),
            "error": str(e)
        }
        
        logger.error("Database health check failed", 
                    error=e,
                    context=health_info)
        
        return health_info

def get_connection_pool_stats() -> Dict[str, Any]:
    """
    Get database connection pool statistics (placeholder for future implementation).
    
    Returns:
        Dictionary with connection pool statistics
    """
    # This is a placeholder for future connection pooling implementation
    logger.debug("Connection pool stats requested (not implemented)")
    
    return {
        "pool_enabled": False,
        "active_connections": 0,
        "idle_connections": 0,
        "max_connections": 0
    }
