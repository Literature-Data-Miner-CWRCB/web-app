import os
import requests
import json
import time
import re
from functools import lru_cache
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from typing import List, Dict, Any, Optional, Tuple
import logging
from supabase import create_client, Client
from datetime import datetime
import random
from habanero import Crossref
from abc import ABC, abstractmethod
import json
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# XML namespaces for arXiv API
ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


class ProxyConfig(ABC):
    """
    Abstract base class for proxy configurations.
    """

    @abstractmethod
    def get_proxies(self) -> Dict[str, str]:
        """
        Get the proxies dictionary to be used with requests.

        Returns:
            Dictionary mapping protocols to proxy URLs
        """
        pass

    @property
    def retries_when_blocked(self) -> int:
        """
        Number of retries to perform when a request is blocked.

        Returns:
            Number of retries
        """
        return 3


class WebshareProxyConfig(ProxyConfig):
    """
    Configuration for using Webshare proxies.
    """

    def __init__(
        self,
        proxy_username: str,
        proxy_password: str,
        rotating: bool = True,
        proxy_host: str = None,
        proxy_port: str = None,
        retries: int = 5,
    ):
        """
        Initialize Webshare proxy configuration.

        Args:
            proxy_username: Webshare proxy username
            proxy_password: Webshare proxy password
            rotating: Whether to use rotating residential proxies
            proxy_host: Webshare proxy host (only needed if rotating=False)
            proxy_port: Webshare proxy port (only needed if rotating=False)
            retries: Number of retries when blocked
        """
        self._proxy_username = proxy_username
        self._proxy_password = proxy_password
        self._rotating = rotating
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port
        self._retries = retries

    def get_proxies(self) -> Dict[str, str]:
        """
        Get the Webshare proxies dictionary to be used with requests.

        Returns:
            Dictionary mapping protocols to proxy URLs
        """
        if self._rotating:
            # Use rotating residential proxies from Webshare
            return {
                "http": f"http://{self._proxy_username}:{self._proxy_password}@p.webshare.io:80",
                "https": f"http://{self._proxy_username}:{self._proxy_password}@p.webshare.io:80",
            }
        else:
            # Use specific proxy host and port
            return {
                "http": f"http://{self._proxy_username}:{self._proxy_password}@{self._proxy_host}:{self._proxy_port}",
                "https": f"http://{self._proxy_username}:{self._proxy_password}@{self._proxy_host}:{self._proxy_port}",
            }

    @property
    def retries_when_blocked(self) -> int:
        """
        Number of retries to perform when a request is blocked.

        Returns:
            Number of retries
        """
        return self._retries


class PaperDownloader:
    SCIHUB_PUBLIC_URL = "https://www.sci-hub.pub/"  # Scihub main public repo where the list of Sci-Hub mirrors to try - these change frequently

    def __init__(
        self,
        webshare_proxy_user: str,
        webshare_proxy_pass: str,
        webshare_proxy_host: str,
        webshare_proxy_port: str,
        supabase_url: str,
        supabase_key: str,
        download_dir: str = "papers",
        max_retries: int = 3,
        retry_delay: int = 5,
        rotating_proxies: bool = True,
    ):
        """
        Initialize the PaperDownloader with proxy and Supabase credentials.

        Args:
            webshare_proxy_user: Webshare proxy username
            webshare_proxy_pass: Webshare proxy password
            webshare_proxy_host: Webshare proxy host
            webshare_proxy_port: Webshare proxy port
            supabase_url: Supabase project URL
            supabase_key: Supabase project API key
            download_dir: Local directory to temporarily store papers
            max_retries: Maximum number of retries for network operations
            retry_delay: Delay between retries in seconds
            rotating_proxies: Whether to use rotating residential proxies
        """
        # Create proxy configuration
        if rotating_proxies:
            self.proxy_config = WebshareProxyConfig(
                proxy_username=webshare_proxy_user,
                proxy_password=webshare_proxy_pass,
                rotating=True,
            )
        else:
            self.proxy_config = WebshareProxyConfig(
                proxy_username=webshare_proxy_user,
                proxy_password=webshare_proxy_pass,
                rotating=False,
                proxy_host=webshare_proxy_host,
                proxy_port=webshare_proxy_port,
            )

        # Initialize Supabase client
        self.supabase: Client = create_client(supabase_url, supabase_key)
        print("Logging in to Supabase...")
        supabase_auth_response = self.supabase.auth.sign_in_with_password(
            {"email": "admin@dataminer.com", "password": "admin"}
        )
        if not supabase_auth_response:
            raise Exception("Failed to login admin")
        supabase_session = supabase_auth_response.session
        self.supabase.auth.set_session(
            access_token=supabase_session.access_token,
            refresh_token=supabase_session.refresh_token,
        )

        # Create download directory if it doesn't exist
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)

        # Retry configuration
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Set up session with proxy
        self.session = self._create_session()

        # Track proxy failures
        self.proxy_failures = 0
        self.max_proxy_failures = (
            10  # After this many failures, wait longer before trying again
        )

    def _generate_random_browser_fingerprint(self):
        """
        Generate a random but realistic browser fingerprint.

        Returns:
            Tuple of (user_agent, headers)
        """
        # More diverse and realistic user agents
        user_agents = [
            # Chrome
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
            # Firefox
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:95.0) Gecko/20100101 Firefox/95.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0",
            # Safari
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
            # Edge
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
        ]

        user_agent = random.choice(user_agents)

        # Generate random but plausible accept headers based on browser type
        if "Chrome" in user_agent:
            accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
            accept_language = "en-US,en;q=0.9"
            accept_encoding = "gzip, deflate, br"
        elif "Firefox" in user_agent:
            accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            accept_language = "en-US,en;q=0.5"
            accept_encoding = "gzip, deflate, br"
        elif "Safari" in user_agent:
            accept = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            accept_language = "en-US,en;q=0.9"
            accept_encoding = "gzip, deflate, br"
        else:
            accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            accept_language = "en-US,en;q=0.9"
            accept_encoding = "gzip, deflate, br"

        # Random cache-control strategy
        cache_controls = [
            "max-age=0",
            "no-cache",
            "no-store, max-age=0",
            None,  # Some browsers don't send this header
        ]

        # Generate realistic headers based on the selected browser
        headers = {
            "User-Agent": user_agent,
            "Accept": accept,
            "Accept-Language": accept_language,
            "Accept-Encoding": accept_encoding,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }

        # Add cache-control if selected
        cache_control = random.choice(cache_controls)
        if cache_control:
            headers["Cache-Control"] = cache_control

        # Remove None values
        headers = {k: v for k, v in headers.items() if v is not None}

        return user_agent, headers

    def _create_session(self) -> requests.Session:
        """
        Create a new requests session with proxy configuration.

        Returns:
            Configured requests.Session
        """
        session = requests.Session()
        session.proxies.update(self.proxy_config.get_proxies())

        _, headers = self._generate_random_browser_fingerprint()
        session.headers.update(headers)

        # Set cookies jar
        session.cookies.clear()

        return session

    def _reset_session(self):
        """
        Reset the session to use potentially a new proxy from the rotating pool.
        """
        self.session.close()
        time.sleep(2)  # Wait before creating a new session
        self.session = self._create_session()

    def _make_request_with_retry(self, method, url, max_retries=3, **kwargs):
        """Make a request with automatic retries for 403 errors"""
        for attempt in range(max_retries):
            try:
                response = getattr(self.session, method.lower())(url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403 and attempt < max_retries - 1:
                    logger.warning(f"403 Forbidden, attempt {attempt+1}/{max_retries}")

                    # Graduated backoff with jitter
                    delay = (2**attempt) + random.uniform(0, 1)
                    time.sleep(delay)

                    # Only reset the session after first simple retry
                    if attempt >= 0:  # Reset on first failure or later
                        self._reset_session()
                else:
                    raise

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make an HTTP request with the session.

        Args:
            method: HTTP method (get, post, etc.)
            url: URL to request
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        try:
            response = getattr(self.session, method.lower())(url, **kwargs)
            # response = requests.get(url, proxies=self.proxy_config.get_proxies()) # Comment out direct requests.get

            # Check if the response was successful
            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {url} - {str(e)}")
            raise

    def _search_crossref(
        self,
        query: str,
        min_year: int,
        max_results: int,
        max_year: int = None,
        author: str = None,
        affiliation: str = None,
        funder_id: str = None,
        has_orcid: bool = None,
        has_full_text: bool = None,
        document_type: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for papers using the Crossref API via habanero.

        Args:
            query: The search query
            min_year: Minimum publication year
            max_year: Maximum publication year (inclusive)
            max_results: Maximum number of results to return
            author: Specific author name to search for
            affiliation: Institution affiliation to search for (may have limited results)
            funder_id: Funder ID to filter by (e.g., '10.13039/100000001' for NSF)
            has_orcid: If True, only returns papers with ORCID identifiers
            has_full_text: If True, only returns papers with full-text links
            document_type: Type of document (e.g., 'journal-article', 'book-chapter')

        Returns:
            A list of paper metadata
        """
        print(f"Searching Crossref for: {query}, from year {min_year}")

        # Build filter dictionary
        filter_dict = {
            "from-pub-date": str(min_year),
        }

        # Add optional filters
        if max_year:
            filter_dict["until-pub-date"] = str(max_year)

        if document_type:
            filter_dict["type"] = document_type
        else:
            # Default to journal articles if not specified
            filter_dict["type"] = "journal-article"

        if has_orcid is not None:
            filter_dict["has-orcid"] = "true" if has_orcid else "false"

        if has_full_text is not None:
            filter_dict["has-full-text"] = "true" if has_full_text else "false"

        if funder_id:
            filter_dict["funder"] = funder_id

        # Prepare additional query parameters
        additional_params = {}

        # Add field-specific queries
        if author:
            additional_params["query_author"] = author

        if affiliation:
            additional_params["query_affiliation"] = affiliation
            logger.warning(
                "Note: Affiliation search in Crossref is limited and may not return all relevant results"
            )

        papers = []
        try:
            # Initialize Crossref client with a proper mailto for polite pool
            cr = Crossref(
                mailto="user@example.com", timeout=60
            )  # Replace with your email

            # Search for papers with increased timeout
            results = cr.works(
                query=query,
                filter=filter_dict,
                limit=max_results,
                sort="relevance",
                **additional_params,
            )

            if not "message" in results or not "items" in results["message"]:
                logger.error(f"Unexpected response structure from Crossref: {results}")
                return []

            # Process results from Crossref
            for item in results["message"]["items"]:
                # Check if we've reached the maximum number of results
                if len(papers) >= max_results:
                    break
                # Extract the DOI
                doi = item.get("DOI")
                if not doi:
                    continue

                # Extract title
                title = ""
                if "title" in item and item["title"]:
                    title = item["title"][0]

                # Extract authors
                authors = []
                if "author" in item:
                    for author in item["author"]:
                        if "given" in author and "family" in author:
                            authors.append(
                                f"{author.get('given', '')} {author.get('family', '')}"
                            )
                        elif "family" in author:
                            authors.append(author.get("family", ""))

                # Extract year
                year = None
                if (
                    "published-print" in item
                    and "date-parts" in item["published-print"]
                ):
                    year = item["published-print"]["date-parts"][0][0]
                elif (
                    "published-online" in item
                    and "date-parts" in item["published-online"]
                ):
                    year = item["published-online"]["date-parts"][0][0]
                elif "created" in item and "date-parts" in item["created"]:
                    year = item["created"]["date-parts"][0][0]

                if year and int(year) < min_year:
                    continue

                # Extract URL
                url = f"https://doi.org/{doi}"

                # Get potential PDF URLs
                pdf_url = None
                if "link" in item:
                    for link in item["link"]:
                        if "URL" in link and (
                            "pdf" in link.get("content-type", "").lower()
                            or "pdf" in link.get("URL", "").lower()
                        ):
                            pdf_url = link["URL"]
                            break

                # Extract abstract
                abstract = ""
                if "abstract" in item:
                    abstract = item["abstract"]

                papers.append(
                    {
                        "title": title,
                        "authors": authors,
                        "year": year,
                        "url": url,
                        "pdf_url": pdf_url,
                        "source": "Crossref",
                        "doi": doi,
                        "abstract": abstract,
                    }
                )
        except Exception as e:
            # Handle other exceptions
            logger.error(f"Error searching Crossref: {str(e)}")

        logger.info(f"Found {len(papers)} papers on Crossref")
        return papers

    def _search_arxiv(
        self, query: str, min_year: int, max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Search for papers using the arXiv API.

        Args:
            query: The search query
            min_year: Minimum publication year
            max_results: Maximum number of results to return

        Returns:
            A list of paper metadata
        """
        print(f"Searching arXiv for: {query}, from year {min_year}")

        # Format the query for arXiv
        # Note: arXiv doesn't directly support year filtering in API, so we'll filter results later
        formatted_query = quote_plus(query)
        url = f"http://export.arxiv.org/api/query?search_query=all:{formatted_query}&start=0&max_results={max_results*2}"  # Request more to account for year filtering

        try:
            # response = self._make_request("get", url)
            response = self._make_request_with_retry("get", url)

            # Parse the XML response
            root = ET.fromstring(response.content)

            papers = []
            for entry in root.findall(".//atom:entry", ARXIV_NS):
                # Extract basic metadata
                title = entry.find("atom:title", ARXIV_NS).text.strip()

                # Extract authors
                authors = []
                for author in entry.findall(".//atom:author/atom:name", ARXIV_NS):
                    authors.append(author.text.strip())

                # Extract URLs
                url = entry.find("atom:id", ARXIV_NS).text.strip()
                pdf_url = url.replace("abs", "pdf") + ".pdf"

                # Extract publication date
                published = entry.find("atom:published", ARXIV_NS).text.strip()
                year = int(published.split("-")[0])

                # Extract arXiv ID for DOI formation
                arxiv_id = url.split("/")[-1]
                doi = f"10.48550/arXiv.{arxiv_id}"

                # Filter by year
                if year >= min_year:
                    papers.append(
                        {
                            "title": title,
                            "authors": authors,
                            "year": year,
                            "url": url,
                            "pdf_url": pdf_url,
                            "source": "arXiv",
                            "doi": doi,
                            "abstract": entry.find(
                                "atom:summary", ARXIV_NS
                            ).text.strip(),
                        }
                    )

                if len(papers) >= max_results:
                    break

            logger.info(f"Found {len(papers)} papers on arXiv")
            return papers

        except Exception as e:
            logger.error(f"Error searching arXiv: {str(e)}")
            return []

    def _search_semantic_scholar(
        self, query: str, min_year: int, max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Search for papers using the Semantic Scholar API.

        Args:
            query: The search query
            min_year: Minimum publication year
            max_results: Maximum number of results to return

        Returns:
            A list of paper metadata
        """
        print(f"Searching Semantic Scholar for: {query}, from year {min_year}")

        url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
        params = {
            "query": query,
            "year": f"{min_year}-",  # Year range filter
            "limit": max_results,
            "fields": "title,authors,year,url,venue,publicationTypes,openAccessPdf,abstract,externalIds",
        }

        # headers = {
        #     "x-api-key":
        # }

        try:
            response = self._make_request("get", url, params=params)
            data = response.json()

            papers = []
            for paper in data.get("data", []):
                # Extract DOI if available
                doi = None
                if paper.get("externalIds") and "DOI" in paper.get("externalIds", {}):
                    doi = paper.get("externalIds", {}).get("DOI")

                # Create paper entry whether or not PDF is available (we'll try to download using SciHub later)
                papers.append(
                    {
                        "title": paper.get("title", ""),
                        "authors": [
                            author.get("name", "")
                            for author in paper.get("authors", [])
                        ],
                        "year": paper.get("year"),
                        "url": paper.get("url", ""),
                        "pdf_url": paper.get("openAccessPdf", {}).get("url", ""),
                        "source": "Semantic Scholar",
                        "doi": doi,
                        "abstract": paper.get("abstract", ""),
                    }
                )

            logger.info(f"Found {len(papers)} papers on Semantic Scholar")
            return papers

        except Exception as e:
            logger.error(f"Error searching Semantic Scholar: {str(e)}")
            return []

    @lru_cache(maxsize=1)
    def _get_working_scihub_links(self) -> List[str]:
        """
        Get a list of Sci-Hub links that are currently working by scraping
        the main Sci-Hub public URL and testing potential mirrors.

        Returns:
            List of working Sci-Hub links
        """
        logger.info(
            f"Attempting to find working Sci-Hub mirrors from {self.SCIHUB_PUBLIC_URL}"
        )
        potential_mirrors = []
        working_mirrors = []

        try:
            # 1. Get the main page content
            main_response = self._make_request(
                "get", self.SCIHUB_PUBLIC_URL, timeout=(10, 20)
            )
            soup = BeautifulSoup(main_response.text, "html.parser")

            # 2. Find all links that look like Sci-Hub domains
            #    More robust: find all <a> tags and check href
            for a in soup.find_all("a", href=True):
                link = a["href"]
                # Basic check for http/https and sci-hub domain pattern
                if re.match(r"https?://(www\\.)?sci-hub\\.", link):
                    # Ensure the link has a scheme, default to https if missing
                    if not link.startswith("http"):
                        link = (
                            "https:" + link
                            if link.startswith("//")
                            else "https://" + link
                        )
                    if link not in potential_mirrors:  # Avoid duplicates
                        potential_mirrors.append(link)

            logger.info(f"Found {len(potential_mirrors)} potential Sci-Hub mirrors.")

            # 3. Test potential mirrors one by one with delays and timeouts
            for mirror_url in potential_mirrors:
                logger.debug(f"Testing mirror: {mirror_url}")
                try:
                    # Add a small delay to be polite
                    time.sleep(random.uniform(0.5, 1.5))
                    # Test the mirror with a timeout
                    test_response = self._make_request(
                        "get", mirror_url, timeout=(5, 15)
                    )  # Shorter timeout for tests
                    if test_response.status_code == 200:
                        logger.info(f"Confirmed working mirror: {mirror_url}")
                        working_mirrors.append(mirror_url)
                    else:
                        logger.debug(
                            f"Mirror {mirror_url} returned status {test_response.status_code}"
                        )
                except requests.exceptions.RequestException as test_e:
                    logger.warning(f"Mirror {mirror_url} failed test: {str(test_e)}")
                except Exception as inner_e:
                    logger.warning(
                        f"Unexpected error testing mirror {mirror_url}: {str(inner_e)}"
                    )

            if not working_mirrors:
                logger.warning(
                    "Could not find any working Sci-Hub mirrors from the public list."
                )

            return working_mirrors

        except requests.exceptions.RequestException as req_e:
            logger.error(
                f"Failed to fetch Sci-Hub public URL {self.SCIHUB_PUBLIC_URL}: {str(req_e)}"
            )
            return []  # Return empty list if we can't even get the main page
        except Exception as e:
            logger.error(f"Error getting working Sci-Hub links: {str(e)}")
            return []  # Return empty list on other unexpected errors

    def _parse_pdf_url_from_scihub_page(self, html: str) -> str:
        """
        Extract the PDF URL from the Sci-Hub page.

        Args:
            mirror: Sci-Hub mirror URL
            html: HTML content of the Sci-Hub page

        Returns:
            PDF URL if found, otherwise an empty string
        """
        soup = BeautifulSoup(html, "html.parser")
        pdf_url = None

        # Method 1: Look for the PDF iframe with id='pdf'
        iframe = soup.find("iframe", id="pdf")
        if iframe and iframe.get("src"):
            pdf_url = iframe.get("src")
            logger.info(f"Found PDF URL in iframe: {pdf_url}")

        # Method 2: Look for download links with "save" text or download icons
        if not pdf_url:
            save_links = soup.find_all(
                "a", text=lambda t: t and ("save" in t.lower() or "⇣" in t)
            )
            for link in save_links:
                # Check for onclick attribute with PDF URL
                onclick = link.get("onclick")
                if onclick and ".pdf" in onclick:
                    # Extract URL from javascript
                    import re

                    match = re.search(
                        r"['\"](https?://[^'\"]+\.pdf[^'\"]*)['\"]", onclick
                    )
                    if match:
                        pdf_url = match.group(1).replace("\\/", "/")
                        logger.info(f"Found PDF URL in onclick attribute: {pdf_url}")
                        break

        # Method 3: If still no PDF URL, look for any links to PDF files
        if not pdf_url:
            pdf_links = soup.find_all("a", href=lambda h: h and ".pdf" in h)
            if pdf_links:
                pdf_url = pdf_links[0].get("href")
                logger.info(f"Found PDF URL in general link: {pdf_url}")

            if pdf_url:
                # Clean up the URL - remove fragments but keep query parameters
                pdf_url = pdf_url.split("#")[0]

        logger.info(f"Found PDF URL: {pdf_url}")
        return pdf_url

    def _download_from_scihub(self, doi: str, filepath: str) -> bool:
        """
        Try to download a paper from Sci-Hub given its DOI.

        Args:
            doi: DOI of the paper
            filepath: Path where to save the downloaded paper

        Returns:
            True if download was successful, False otherwise
        """
        if not doi:
            return False

        logger.info(f"Attempting to download {doi} from Sci-Hub")

        # List of Sci-Hub mirrors to try - these change frequently
        # This list needs to be updated periodically
        mirrors = [
            # "https://sci-hub.ru",
            # "https://sci-hub.se",
            # "https://sci-hub.st",
            # "https://sci-hub.box",
            # "https://sci-hub.red",
            # "https://sci-hub.al",
            "https://sci-hub.ee",
            # "https://sci-hub.lu",
            # "https://sci-hub.ren",
            # "https://sci-hub.shop",
            # "https://sci-hub.vg",
        ]
        # mirrors = self._get_working_scihub_links()

        # Randomly shuffle mirrors to distribute load
        random.shuffle(mirrors)

        # Add random delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))

        # Try each mirror until successful or all fail
        for i, mirror in enumerate(mirrors):
            try:
                # Construct the Sci-Hub URL for the DOI
                url = f"{mirror}/{doi}"
                print(f"Trying Sci-Hub mirror: {mirror}")

                # Make a request to the Sci-Hub page
                try:
                    # response = self._make_request("get", url, timeout=(10, 30))
                    response = self._make_request_with_retry(
                        "get", url, timeout=(10, 30)
                    )
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Failed to access {mirror}: {str(e)}")
                    continue  # Try next mirror

                # Check if we got a successful response
                if response.status_code != 200:
                    logger.warning(
                        f"Mirror {mirror} returned status code {response.status_code}"
                    )
                    continue  # Try next mirror

                # Try to parse the HTML to find the PDF link
                try:
                    pdf_url = self._parse_pdf_url_from_scihub_page(response.text)
                    if not pdf_url:
                        logger.warning(f"No PDF URL found for {doi} on mirror {mirror}")
                        continue  # Try next mirror

                    # Try to download the PDF with a longer timeout
                    try:
                        # Add the Referer header pointing back to the Sci-Hub DOI page
                        pdf_headers = {"Referer": url}  # url is f"{mirror}/{doi}"
                        # pdf_response = self._make_request(
                        pdf_response = self._make_request_with_retry(
                            "get",
                            pdf_url,
                            stream=True,
                            timeout=(15, 120),
                            headers=pdf_headers,
                        )

                        # Check if the response is a PDF
                        content_type = pdf_response.headers.get("Content-Type", "")
                        if (
                            "application/pdf" in content_type
                            or "octet-stream" in content_type
                        ):
                            with open(filepath, "wb") as f:
                                for chunk in pdf_response.iter_content(chunk_size=8192):
                                    if chunk:  # Filter out keep-alive chunks
                                        f.write(chunk)

                            # Verify the file is a valid PDF
                            with open(filepath, "rb") as f:
                                header = f.read(4)
                                if header == b"%PDF":
                                    print(
                                        f"Successfully downloaded {doi} from Sci-Hub mirror {mirror}"
                                    )
                                    return True
                                else:
                                    logger.warning(
                                        f"Downloaded file is not a valid PDF, removing {filepath}"
                                    )
                                    os.remove(filepath)
                        else:
                            logger.warning(
                                f"Response from {pdf_url} is not a PDF: {content_type}"
                            )
                    except requests.exceptions.RequestException as e:
                        logger.warning(
                            f"Failed to download PDF from {pdf_url}: {str(e)}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Error parsing Sci-Hub page from {mirror}: {str(e)}"
                    )
            except Exception as e:
                logger.warning(f"Error processing mirror {mirror}: {str(e)}")

        logger.warning(f"Failed to download {doi} from all Sci-Hub mirrors")
        return False

    def _download_from_url(self, url: str, filepath: str) -> bool:
        """
        Download a paper from a direct URL.

        Args:
            url: URL to the PDF
            filepath: Path where to save the downloaded paper

        Returns:
            True if download was successful, False otherwise
        """
        try:
            # Basic headers for any file download
            headers = {
                "User-Agent": random.choice(
                    [
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
                    ]
                ),
                "Accept": "application/pdf,application/octet-stream,*/*",
                "Referer": url,
            }

            # Add domain-specific headers for common academic publishers
            domain = url.split("/")[2] if len(url.split("/")) > 2 else ""

            if "mdpi.com" in domain:
                # MDPI specific headers
                headers.update(
                    {
                        "Accept": "application/pdf",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "same-origin",
                        "Sec-Fetch-User": "?1",
                        "Upgrade-Insecure-Requests": "1",
                        # Referer should point to the article page rather than the PDF itself
                        "Referer": url.replace("/pdf", ""),
                    }
                )
            elif "sciencedirect.com" in domain:
                # ScienceDirect specific headers
                headers.update(
                    {
                        "Accept": "application/pdf",
                        "Origin": "https://www.sciencedirect.com",
                        "Sec-Fetch-Dest": "document",
                    }
                )
            elif "springer.com" in domain or "link.springer.com" in domain:
                # Springer specific headers
                headers.update(
                    {
                        "Accept": "application/pdf",
                        "Origin": "https://link.springer.com",
                    }
                )
            elif "wiley.com" in domain or "onlinelibrary.wiley.com" in domain:
                # Wiley specific headers
                headers.update(
                    {
                        "Accept": "application/pdf",
                        "Origin": "https://onlinelibrary.wiley.com",
                    }
                )
            elif "nature.com" in domain:
                # Nature specific headers
                headers.update(
                    {
                        "Accept": "application/pdf",
                        "Origin": "https://www.nature.com",
                    }
                )

            # Use the retry-enabled request method
            response = self._make_request_with_retry(
                "get", url, headers=headers, stream=True, timeout=(15, 120)
            )

            # Check if the response is a PDF or downloadable content
            content_type = response.headers.get("Content-Type", "").lower()
            if (
                "application/pdf" in content_type
                or "octet-stream" in content_type
                or "application/x-download" in content_type
            ):

                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)

                # Verify the file is a valid PDF
                with open(filepath, "rb") as f:
                    header = f.read(4)
                    if header == b"%PDF":
                        logger.info(f"Successfully downloaded paper from direct URL")
                        return True
                    else:
                        logger.warning(
                            f"Downloaded file is not a valid PDF, removing {filepath}"
                        )
                        os.remove(filepath)
                        return False
            else:
                logger.warning(f"Response is not a PDF: {content_type}")
                return False

        except Exception as e:
            logger.warning(f"Failed to download from URL: {str(e)}")
            return False

    # FIXME: not working
    def _download_from_doi(self, doi: str, filepath: str) -> bool:
        """
        Try to download a paper by going to its DOI URL and scraping for PDF links.

        Args:
            doi: DOI of the paper
            filepath: Path where to save the downloaded paper

        Returns:
            True if download was successful, False otherwise
        """
        try:
            # Construct the DOI URL
            doi_url = f"https://doi.org/{doi}"
            logger.info(f"Accessing DOI URL: {doi_url}")

            # Make a request to the DOI URL
            # Use a longer timeout as DOI resolution can be slow
            response = self._make_request(
                "get",
                doi_url,
                timeout=(15, 30),
                headers={"Accept": "text/html,application/xhtml+xml,application/xml"},
            )

            # Check for redirection to the publisher's page
            if len(response.history) > 0:
                publisher_url = response.url
                logger.info(f"DOI resolved to publisher URL: {publisher_url}")

                soup = BeautifulSoup(response.content, "html.parser")

                # Look for PDF links in various common formats used by publishers
                pdf_links = []

                # Method 1: Look for links with PDF in the text or href
                for link in soup.find_all("a"):
                    href = link.get("href", "")
                    text = link.get_text().lower()

                    if "pdf" in href.lower() or "pdf" in text:
                        if href.startswith("/"):
                            # Handle relative URLs
                            base_url = (
                                response.url.split("//")[0]
                                + "//"
                                + response.url.split("//")[1].split("/")[0]
                            )
                            href = base_url + href
                        elif not href.startswith(("http://", "https://")):
                            # Handle other relative URLs
                            base_url = "/".join(response.url.split("/")[:-1])
                            href = f"{base_url}/{href}"

                        pdf_links.append(href)
                        logger.info(f"Found potential PDF link: {href}")

                # Method 2: Look for meta tags that might indicate PDF URLs
                for meta in soup.find_all("meta"):
                    if "citation_pdf_url" in meta.get("name", "").lower():
                        pdf_url = meta.get("content", "")
                        if pdf_url:
                            pdf_links.append(pdf_url)
                            logger.info(f"Found PDF URL in meta tag: {pdf_url}")

                # Try to download from each potential PDF link
                for pdf_url in pdf_links:
                    logger.info(
                        f"Attempting to download from potential PDF link: {pdf_url}"
                    )
                    if self._download_from_url(pdf_url, filepath):
                        return True

                # If we get here, none of the PDF links worked
                logger.warning(
                    f"Found {len(pdf_links)} potential PDF links, but none worked"
                )

                # As a last resort, check if the page itself is a PDF
                content_type = response.headers.get("Content-Type", "").lower()
                if "application/pdf" in content_type:
                    logger.info(f"Publisher page is itself a PDF, downloading directly")
                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    # Verify the file is a valid PDF
                    with open(filepath, "rb") as f:
                        header = f.read(4)
                        if header == b"%PDF":
                            logger.info(
                                f"Successfully downloaded PDF directly from publisher"
                            )
                            return True
                        else:
                            logger.warning(f"Downloaded file is not a valid PDF")
                            os.remove(filepath)
            else:
                logger.warning(f"DOI did not resolve properly: {doi_url}")

            return False

        except Exception as e:
            logger.warning(f"Failed to download from DOI URL: {str(e)}")
            return False

    def test_download_from_doi(self, doi: str):
        # Construct the DOI URL
        doi_url = f"https://doi.org/{doi}"
        print(f"Accessing DOI URL: {doi_url}")

        # Make a request to the DOI URL
        # Use a longer timeout as DOI resolution can be slow
        response = self._make_request(
            "get",
            doi_url,
            timeout=(15, 30),
            headers={"Accept": "text/html,application/xhtml+xml,application/xml"},
        )

        print("Response: ", response)

        # Check for redirection to the publisher's page
        if len(response.history) > 0:
            publisher_url = response.url
            print(f"DOI resolved to publisher URL: {publisher_url}")

            soup = BeautifulSoup(response.content, "html.parser")

            print("Html content: ", soup.get_text())

            links = soup.find_all("a")
            print("Links: ", links)

            metadata_tags = soup.find_all("meta")
            print("Tags: ", metadata_tags)

    @lru_cache(maxsize=1024)
    def _check_paper_exists(self, doi: str) -> bool:
        """
        Check if we already have a paper with the same DOI in our database.

        Args:
            doi: The DOI of the paper

        Returns:
            True if paper already exists, False otherwise
        """
        if not doi:
            return False

        papers_in_db = (
            self.supabase.table("papers").select("*").eq("doi", doi).execute()
        )
        return len(papers_in_db.data) > 0

    def search_papers(
        self, query: str, min_year: int, max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search for papers using multiple sources based on a query and minimum year.

        Args:
            query: The search query
            min_year: Minimum publication year
            max_results: Maximum number of results to return

        Returns:
            A list of paper metadata
        """
        papers = []
        results_needed = max_results

        # Try different sources until we have enough results or exhausted all sources
        for source_func in [
            self._search_crossref,
            self._search_arxiv,
            self._search_semantic_scholar,
        ]:
            if results_needed <= 0:
                break

            source_papers = source_func(query, min_year, results_needed)

            # Deduplicate papers by doi (simple approach)
            for paper in source_papers:
                # if paper already exists, skip
                if any(p.get("doi") == paper.get("doi") for p in papers):
                    continue

                # if paper already exists in the database, skip
                if self._check_paper_exists(paper.get("doi", "")):
                    continue

                papers.append(paper)
                results_needed -= 1

        return papers

    def download_paper(self, paper: Dict[str, Any]) -> Optional[str]:
        """
        Download a paper based on its metadata, trying multiple approaches.

        Args:
            paper: Paper metadata containing URL, title, etc.

        Returns:
            Path to the downloaded file, or None if download failed
        """
        try:
            # Create a safe filename
            title = paper.get("title", "unknown")
            safe_title = "".join(c if c.isalnum() or c == " " else "_" for c in title)
            safe_title = safe_title[:100].strip()  # Limit filename length
            year = paper.get("year", "0000")
            author = (
                paper.get("authors", ["unknown"])[0].split()[-1]
                if paper.get("authors")
                else "unknown"
            )
            doi = paper.get("doi", "")

            # Use DOI in filename if available
            if doi:
                # Replace potentially problematic characters in DOI
                safe_doi = doi.replace("/", "_").replace(".", "_")
                filename = f"{safe_doi}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            else:
                filename = f"{author}_{year}_{safe_title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"

            filepath = os.path.join(self.download_dir, filename)

            # Approach 1: Try direct download if PDF URL is available
            pdf_url = paper.get("pdf_url")
            if pdf_url:
                print(f"Attempting direct download from pdf url: {pdf_url}")
                if self._download_from_url(pdf_url, filepath):
                    return filepath

            # Approach 2: try Sci-Hub if DOI is available
            if doi:
                print(f"Attempting Sci-Hub download for DOI: {doi}")
                if self._download_from_scihub(doi, filepath):
                    return filepath

            # Approach 3: If DOI is available, try to download directly from the DOI URL as a last resort
            # if doi:
            #     print(f"Attempting to download from publisher via DOI: {doi}")
            #     if self._download_from_doi(doi, filepath):
            #         return filepath

            # If all attempts failed
            logger.warning(f"Failed to download paper: {title}")
            return None

        except Exception as e:
            logger.error(f"Error in download process: {str(e)}")
            return None

    def _hash_dict(self, data: Dict[str, Any]) -> str:
        """
        Generate a hash value for a dictionary.

        Args:
            data: Dictionary to hash

        Returns:
            Hash value as a string
        """
        dict_string = json.dumps(data, sort_keys=True).encode("utf-8")
        return hashlib.md5(dict_string).hexdigest()

    def upload_to_supabase(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Upload a paper to Supabase storage.

        Args:
            filepath: Path to the downloaded paper
            metadata: Paper metadata

        Returns:
            True if upload was successful, False otherwise
        """
        try:
            filename = os.path.basename(filepath)
            bucket_name = "papers"
            table_name = "papers"

            # Read file content
            with open(filepath, "rb") as f:
                file_content = f.read()

            # Upload file
            print(f"Uploading paper to Supabase: {filename}")

            # Try to upload, handle possible conflicts
            try:
                # generate hash value from file metadata
                hash_value = self._hash_dict(metadata)
                supabase_storage_path = f"{hash_value}/{filename}"
                signed_url_response = self.supabase.storage.from_(
                    bucket_name
                ).create_signed_upload_url(
                    path=supabase_storage_path,
                )
                self.supabase.storage.from_(bucket_name).upload_to_signed_url(
                    file=file_content,
                    path=signed_url_response["path"],
                    token=signed_url_response["token"],
                    file_options={"content-type": "application/pdf"},
                )
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.warning(f"File already exists in storage.")
                    return True
                else:
                    raise

            # Get public URL
            file_url = self.supabase.storage.from_(bucket_name).get_public_url(filename)

            # Store metadata in a database table
            paper_data = {
                "title": metadata.get("title", "Unknown"),
                "authors": json.dumps(metadata.get("authors", [])),
                "year": metadata.get("year"),
                "source": metadata.get("source", "Unknown"),
                "doi": metadata.get("doi", "Unknown"),
                "original_url": metadata.get("url", ""),
                "storage_path": supabase_storage_path,
                "public_url": file_url,
                "abstract": metadata.get("abstract", ""),
                "has_processed": False,
                "created_at": datetime.now().isoformat(),
            }

            # Create papers table if it doesn't exist
            self._ensure_papers_table_exists()

            print("Storing paper metadata in database")
            self.supabase.table("papers").insert(paper_data).execute()

            # Delete local file
            os.remove(filepath)

            logger.info(f"Successfully uploaded paper to Supabase")
            return True

        except Exception as e:
            logger.error(f"Error uploading to Supabase: {str(e)}")
            return False

    def _ensure_papers_table_exists(self):
        """Ensure the papers table exists in Supabase"""
        try:
            # Check if the table exists by attempting to select from it
            self.supabase.table("papers").select("id").limit(1).execute()
        except Exception:
            # If an error occurs, the table might not exist
            logger.warning(
                "Papers table might not exist. Please create it with the following SQL:"
            )
            logger.warning(
                """
                create table public.papers (
                    id uuid not null default uuid_generate_v4(),
                    title text not null,
                    authors json,
                    year int,
                    source text,
                    original_url text,
                    storage_path text,
                    public_url text,
                    abstract text,
                    created_at timestamp with time zone,
                    has_processed boolean default false,
                    primary key (id)
                );

                alter table public.papers enable row level security;

                create policy "Public papers are viewable by everyone."
                    on papers for select
                    using (true);
            """
            )
