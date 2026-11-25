# DealRadar
A static deal dashboard with daily RSS collection.

- Categories include furniture/sectionals, room heaters, home gym, jackets (including North Face), kids' shoes, tech, kitchen, home, fashion and more.
- Daily GitHub Actions workflow collects public Slickdeals and DealNews RSS listings.
- Each deal links to its retailer destination when the feed explicitly provides one; otherwise it links to the publisher's deal page. No Google search URLs are generated.
- The catalogue targets 500+ offers and retains up to 1,000 unique listings. Actual count depends on public feed availability; the collector never fabricates deals.
- Price/discount values are shown only when present in the feed. Verify current price and stock on the destination site.
- GitHub Pages source should be set to GitHub Actions in repository Settings → Pages.

Deployment pipeline now generates the deal JSON catalogue before packaging the GitHub Pages artifact.
