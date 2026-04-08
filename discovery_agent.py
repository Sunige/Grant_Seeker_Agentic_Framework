"""
What: An agent responsible for dynamically discovering new, unknown grant portals.
Why: Reduces the maintenance burden by auto-updating the list of URLs in config.py if it finds a new permanent grant index using Serper (Google Search).
How: Executes broad queries on Google, extracts the links, verifies they aren't already known, and then uses regex to rewrite `config.py` programmatically.
"""
import os
import requests
import json
import re

class DiscoveryAgent:
    """
    What: System agent for maintaining and expanding the source URL list.
    Why: Allows the application to run semi-autonomously by discovering its own new sources.
    How: Uses SERPER_API_KEY to search Google and appends results to config.py safely.
    """
    def __init__(self, search_queries, existing_urls):
        self.search_queries = search_queries
        self.existing_urls = existing_urls
        
    def discover_and_add(self):
        """
        What: The main routine to find and register new URLs.
        Why: We want the framework to continuously grow its coverage over time without manual intervention.
        How: Uses Serper API to perform google searches. Filters out any URLs already in `self.existing_urls` avoiding duplicates, then triggers `_update_config_py`.
        """
        api_key = os.environ.get("SERPER_API_KEY")
        if not api_key:
            print("[Discovery Agent] No SERPER_API_KEY. Skipping new link discovery.")
            return

        print(f"\n[Discovery Agent] Searching the web to discover NEW permanent grant portals...")
        url = "https://google.serper.dev/search"
        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
        
        new_links_found = []
        for query in self.search_queries:
            # We want to find general grant portals or open competition pages
            payload = json.dumps({"q": query + " funding portal OR apply", "num": 3}) 
            try:
                response = requests.request("POST", url, headers=headers, data=payload)
                response.raise_for_status()
                organic = response.json().get("organic", [])
                
                for res in organic:
                    link = res.get("link", "")
                    # Simple filter to avoid adding huge generic domains like generic google
                    if link.startswith("http") and link not in self.existing_urls and link not in new_links_found:
                        new_links_found.append(link)
            except Exception as e:
                print(f"[Discovery Agent] Failed on query '{query}': {e}")
                
        if new_links_found:
            print(f"[Discovery Agent] Discovered {len(new_links_found)} new potential URLs!")
            self._update_config_py(new_links_found)
            self.existing_urls.extend(new_links_found)
        else:
            print("[Discovery Agent] No new unique URLs discovered this run.")
            
        return self.existing_urls

    def _update_config_py(self, new_links):
        """
        What: Helper routine that actually writes new links to disk.
        Why: We need a persistent way to save dynamically discovered URLs so they aren't lost when the script stops.
        How: Reads config.py as a raw string, uses regex to locate the exact `TARGET_URLS` array string block, injects the new URLs safely, and rewrites the file.
        """
        config_path = "config.py"
        try:
            with open(config_path, "r") as f:
                content = f.read()

            # We use regex to find where the array ends.
            # Look for TARGET_URLS = [ ... ]
            match = re.search(r'(TARGET_URLS\s*=\s*\[)(.*?)(\])', content, re.DOTALL)
            if match:
                prefix = match.group(1)
                array_content = match.group(2).strip()
                suffix = match.group(3)
                
                new_array_lines = []
                if array_content:
                    if not array_content.endswith(','):
                        array_content += ','
                    new_array_lines.append(array_content)
                
                for link in new_links:
                    new_array_lines.append(f'    "{link}",')
                
                # Remove trailing comma on last item
                last_line = new_array_lines[-1]
                if last_line.endswith(','):
                    new_array_lines[-1] = last_line[:-1]
                    
                replacement = prefix + "\n" + "\n".join(new_array_lines) + "\n" + suffix
                new_content = content.replace(match.group(0), replacement)
                
                with open(config_path, "w") as f:
                    f.write(new_content)
                print(f"[Discovery Agent] Successfully appended {len(new_links)} new URLs to config.py!")
            else:
                print("[Discovery Agent] Could not parse TARGET_URLS array in config.py")
        except Exception as e:
            print(f"[Discovery Agent] Failed to update config.py: {e}")
