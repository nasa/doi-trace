from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path


class ReferenceDataSource(ABC):
    """Abstract base class for all reference data sources.
    
    This class defines the interface that all data sources must implement.
    Each data source is responsible for fetching and processing citation data
    from a specific source (e.g., Web of Science, Scopus, etc.).
    """
    
    @abstractmethod
    def fetch_citations(self, dois: List[str], start_date: Optional[str] = None, 
                       end_date: Optional[str] = None) -> Dict[str, Any]:
        """Fetch citations for the given DOIs from the data source.
        
        Args:
            dois: List of DOIs to search for citations
            start_date: Optional start date for the search (format: YYYY-MM-DD)
            end_date: Optional end date for the search (format: YYYY-MM-DD)
            
        Returns:
            Dictionary containing the citation data
        """
        pass
    
    @abstractmethod
    def process_results(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the raw data from the data source into a standardized format.
        
        Args:
            raw_data: Raw data from the data source
            
        Returns:
            Processed data in a standardized format
        """
        pass
    
    @abstractmethod
    def save_results(self, processed_data: Dict[str, Any], output_path: Path) -> None:
        """Save the processed results to a file.
        
        Args:
            processed_data: Processed data to save
            output_path: Path to save the results to
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of the data source.
        
        Returns:
            Name of the data source
        """
        pass
