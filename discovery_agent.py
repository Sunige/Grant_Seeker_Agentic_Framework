import os
import requests
import json
import re

class DiscoveryAgent:
    def __init__(self, search_queries, existing_urls):
        self.search_queries = search_queries
        self.existing_urls = existing_urls
        
    def discover_and_add(self):
        """
        Uses Serper to find new relevant links. 
        If they aren't in existing_urls, it adds them to config.py for future routine checks.
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
        Reads config.py, finds the TARGET_URLS list, and appends the new links, rewriting the file safely.
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
