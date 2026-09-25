import logging
import pdfplumber
from typing import List, Any

logger = logging.getLogger(__name__)

class TableExtractor:
    @staticmethod
    def extract_pdfplumber_tables(file_path: str, ExtractedTable) -> List[Any]:
        """Extract tables using pdfplumber."""
        tables = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    for table in page.find_tables():
                        table_data = table.extract()
                        bbox = table.bbox

                        if not table_data or len(table_data) < 2:
                            continue

                        cleaned = []
                        for row in table_data:
                            cleaned_row = [str(cell).strip() if cell is not None else ""
                                          for cell in row]
                            cleaned.append(cleaned_row)

                        if cleaned and any(any(cell for cell in row) for row in cleaned):
                            tables.append(ExtractedTable(
                                page=page_num + 1,
                                rows=len(cleaned),
                                cols=max(len(row) for row in cleaned),
                                data=cleaned,
                                confidence=0.85,
                                extraction_method="pdfplumber",
                                bbox=list(bbox)
                            ))
                except Exception as e:
                    logger.warning(f"Table extraction failed on page {page_num + 1}: {e}")
        return tables

    @staticmethod
    def extract_camelot(file_path: str, ExtractedTable) -> List[Any]:
        """Extract tables using camelot (no ghostscript needed for lattice mode)."""
        tables = []
        try:
            import camelot
            try:
                lattice_tables = camelot.read_pdf(file_path, pages='all', flavor='lattice')
                for table in lattice_tables:
                    if table.df is not None and not table.df.empty:
                        data = table.df.values.tolist()
                        tables.append(ExtractedTable(
                            page=table.page,
                            rows=len(data),
                            cols=len(data[0]) if data else 0,
                            data=[[str(cell) for cell in row] for row in data],
                            confidence=table.accuracy / 100 if hasattr(table, 'accuracy') else 0.8,
                            extraction_method="camelot-lattice",
                        ))
            except Exception as e:
                logger.warning(f"Camelot lattice mode failed: {e}")

            if len(tables) == 0:
                try:
                    stream_tables = camelot.read_pdf(file_path, pages='all', flavor='stream')
                    for table in stream_tables:
                        if table.df is not None and not table.df.empty:
                            data = table.df.values.tolist()
                            tables.append(ExtractedTable(
                                page=table.page,
                                rows=len(data),
                                cols=len(data[0]) if data else 0,
                                data=[[str(cell) for cell in row] for row in data],
                                confidence=0.75,
                                extraction_method="camelot-stream",
                            ))
                except Exception as e:
                    logger.warning(f"Camelot stream mode failed: {e}")

        except ImportError:
            logger.warning("camelot-py not installed, skipping camelot extraction")
        except Exception as e:
            logger.error(f"Camelot extraction failed: {e}")

        return tables
