#!/usr/bin/env python3
"""
Metadata Enricher Worker

Consumes enrichment jobs from RabbitMQ queue and enriches media metadata
using TMDB API for movie/TV show information and Gemini API for AI-generated descriptions.
"""

import os
import sys
import time
import json
import requests
from typing import Optional, Dict, Any

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared import rabbitmq_client
from shared.db import get_db_connection
from shared.logging_config import configure_logging, get_logger, generate_correlation_id, CorrelationContext
from shared.config import Config

# --- Configuration ---
service_config = Config.get_service_config()

# Configure logging
configure_logging(service_config['name'])
logger = get_logger(service_config['name'])

# API Configuration
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TMDB_BASE_URL = "https://api.themoviedb.org/3"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

class MetadataEnricher:
    """Handles metadata enrichment for media items"""
    
    def __init__(self):
        self.tmdb_available = bool(TMDB_API_KEY)
        self.gemini_available = bool(GEMINI_API_KEY)
        
        if not self.tmdb_available:
            logger.warning("TMDB API key not configured, TMDB enrichment disabled")
        if not self.gemini_available:
            logger.warning("Gemini API key not configured, AI enrichment disabled")
    
    def enrich_metadata(self, media_item_id: int) -> bool:
        """
        Enrich metadata for a media item
        
        Args:
            media_item_id: ID of the media item to enrich
            
        Returns:
            True if enrichment was successful
        """
        conn = get_db_connection()
        if not conn:
            logger.error("Database connection failed for metadata enrichment",
                        context={'media_item_id': media_item_id},
                        severity="critical")
            return False
        
        try:
            with conn.cursor() as cur:
                # Get media item details
                cur.execute("""
                    SELECT id, title, original_file_path, file_path, status
                    FROM media_items 
                    WHERE id = %s AND status = 'pending_enrichment'
                """, (media_item_id,))
                
                media_item = cur.fetchone()
                if not media_item:
                    logger.warning("Media item not found or not pending enrichment",
                                 context={'media_item_id': media_item_id})
                    return False
                
                title = media_item['title']
                logger.info("Starting metadata enrichment",
                           context={
                               'media_item_id': media_item_id,
                               'title': title
                           })
                
                # Enrich with TMDB
                tmdb_data = None
                if self.tmdb_available:
                    tmdb_data = self._enrich_with_tmdb(title)
                
                # Enrich with Gemini AI
                ai_description = None
                if self.gemini_available:
                    ai_description = self._enrich_with_gemini(title, tmdb_data)
                
                # Update database with enriched metadata
                self._update_media_metadata(cur, media_item_id, tmdb_data, ai_description)
                
                # Update status to pending_normalization
                cur.execute("""
                    UPDATE media_items 
                    SET status = 'pending_normalization'
                    WHERE id = %s
                """, (media_item_id,))
                
                conn.commit()
                
                # Publish to normalization queue
                rabbitmq_client.publish_message('normalization_jobs', str(media_item_id))
                
                logger.info("Metadata enrichment completed",
                           context={
                               'media_item_id': media_item_id,
                               'tmdb_enriched': tmdb_data is not None,
                               'ai_enriched': ai_description is not None
                           })
                logger.audit("metadata_enriched", str(media_item_id), context={
                    'title': title,
                    'tmdb_available': tmdb_data is not None,
                    'ai_available': ai_description is not None
                })
                
                return True
                
        except Exception as e:
            logger.error("Failed to enrich metadata",
                        error=e,
                        context={'media_item_id': media_item_id},
                        severity="operational")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def _enrich_with_tmdb(self, title: str) -> Optional[Dict[str, Any]]:
        """Enrich metadata using TMDB API"""
        try:
            # Search for movie/TV show
            search_url = f"{TMDB_BASE_URL}/search/multi"
            params = {
                'api_key': TMDB_API_KEY,
                'query': title,
                'language': 'pt-BR'
            }
            
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('results'):
                logger.info("No TMDB results found", context={'title': title})
                return None
            
            # Get the first result
            result = data['results'][0]
            media_type = result.get('media_type', 'movie')
            
            # Get detailed information
            detail_url = f"{TMDB_BASE_URL}/{media_type}/{result['id']}"
            detail_response = requests.get(detail_url, params={
                'api_key': TMDB_API_KEY,
                'language': 'pt-BR'
            }, timeout=10)
            detail_response.raise_for_status()
            
            detailed_data = detail_response.json()
            
            logger.info("TMDB enrichment successful",
                       context={
                           'title': title,
                           'tmdb_id': result['id'],
                           'media_type': media_type
                       })
            
            return {
                'tmdb_id': result['id'],
                'media_type': media_type,
                'overview': detailed_data.get('overview'),
                'release_date': detailed_data.get('release_date') or detailed_data.get('first_air_date'),
                'genres': [g['name'] for g in detailed_data.get('genres', [])],
                'vote_average': detailed_data.get('vote_average'),
                'poster_path': detailed_data.get('poster_path'),
                'backdrop_path': detailed_data.get('backdrop_path')
            }
            
        except Exception as e:
            logger.error("TMDB enrichment failed",
                        error=e,
                        context={'title': title})
            return None
    
    def _enrich_with_gemini(self, title: str, tmdb_data: Optional[Dict[str, Any]]) -> Optional[str]:
        """Enrich metadata using Gemini AI"""
        try:
            # Create prompt based on available information
            if tmdb_data:
                prompt = f"""
                Baseado nas informações do filme/série "{title}":
                - Tipo: {tmdb_data.get('media_type', 'desconhecido')}
                - Sinopse: {tmdb_data.get('overview', 'Não disponível')}
                - Gêneros: {', '.join(tmdb_data.get('genres', []))}
                - Data de lançamento: {tmdb_data.get('release_date', 'Não disponível')}
                
                Crie uma descrição curta e envolvente (máximo 200 caracteres) para este conteúdo, 
                focando nos aspectos mais interessantes para o público brasileiro.
                """
            else:
                prompt = f"""
                Baseado apenas no título "{title}", crie uma descrição curta e envolvente 
                (máximo 200 caracteres) que possa interessar ao público brasileiro. 
                Se não conseguir identificar o conteúdo, crie uma descrição genérica mas atrativa.
                """
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{GEMINI_BASE_URL}?key={GEMINI_API_KEY}",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if 'candidates' in data and data['candidates']:
                ai_description = data['candidates'][0]['content']['parts'][0]['text'].strip()
                
                logger.info("Gemini AI enrichment successful",
                           context={
                               'title': title,
                               'description_length': len(ai_description)
                           })
                
                return ai_description[:200]  # Ensure max 200 chars
            
            return None
            
        except Exception as e:
            logger.error("Gemini AI enrichment failed",
                        error=e,
                        context={'title': title})
            return None
    
    def _update_media_metadata(self, cur, media_item_id: int, tmdb_data: Optional[Dict[str, Any]], 
                              ai_description: Optional[str]):
        """Update media item with enriched metadata"""
        
        # Prepare metadata JSON
        metadata = {}
        if tmdb_data:
            metadata['tmdb'] = tmdb_data
        if ai_description:
            metadata['ai_description'] = ai_description
        
        # Update the media item
        cur.execute("""
            UPDATE media_items 
            SET 
                description = COALESCE(%s, description),
                metadata = COALESCE(%s, metadata),
                genre = COALESCE(%s, genre),
                release_date = COALESCE(%s, release_date),
                rating = COALESCE(%s, rating),
                updated_at = NOW()
            WHERE id = %s
        """, (
            ai_description or (tmdb_data.get('overview') if tmdb_data else None),
            json.dumps(metadata) if metadata else None,
            ', '.join(tmdb_data.get('genres', [])) if tmdb_data else None,
            tmdb_data.get('release_date') if tmdb_data else None,
            tmdb_data.get('vote_average') if tmdb_data else None,
            media_item_id
        ))

def process_enrichment_job(message_body: str) -> bool:
    """Process a single enrichment job"""
    try:
        media_item_id = int(message_body.strip())
        
        # Generate correlation ID for this job
        correlation_id = generate_correlation_id()
        with CorrelationContext(correlation_id):
            logger.info("Processing enrichment job",
                       context={'media_item_id': media_item_id})
            
            enricher = MetadataEnricher()
            success = enricher.enrich_metadata(media_item_id)
            
            if success:
                logger.info("Enrichment job completed successfully",
                           context={'media_item_id': media_item_id})
            else:
                logger.error("Enrichment job failed",
                            context={'media_item_id': media_item_id})
            
            return success
            
    except ValueError as e:
        logger.error("Invalid message format", error=e, context={'message': message_body})
        return False
    except Exception as e:
        logger.error("Unexpected error processing enrichment job", 
                    error=e, context={'message': message_body})
        return False

def main():
    """Main worker loop"""
    logger.info("Metadata Enricher worker starting")
    
    # Check API availability
    if not TMDB_API_KEY:
        logger.warning("TMDB_API_KEY not configured - TMDB enrichment disabled")
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured - AI enrichment disabled")
    
    if not TMDB_API_KEY and not GEMINI_API_KEY:
        logger.error("No enrichment APIs configured - worker cannot function")
        return
    
    try:
        # Start consuming messages
        rabbitmq_client.consume_messages(
            queue_name='enrichment_jobs',
            callback=process_enrichment_job
        )
    except KeyboardInterrupt:
        logger.info("Metadata Enricher worker stopped by user")
    except Exception as e:
        logger.error("Metadata Enricher worker crashed", error=e, severity="critical")
        raise

if __name__ == "__main__":
    main()