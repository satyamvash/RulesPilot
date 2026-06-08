function Header() {
  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-logo">
          {/* SentinelOne shield icon — inline SVG */}
          <svg
            width="40"
            height="44"
            viewBox="0 0 40 44"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-label="SentinelOne logo"
          >
            {/* Shield outline */}
            <path
              d="M20 2L4 9V22C4 31.5 11.2 40.3 20 43C28.8 40.3 36 31.5 36 22V9L20 2Z"
              fill="rgba(107,47,160,0.25)"
              stroke="rgba(255,255,255,0.6)"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
            {/* Inner shield highlight */}
            <path
              d="M20 6L7 12V22C7 29.8 12.8 37.1 20 39.5C27.2 37.1 33 29.8 33 22V12L20 6Z"
              fill="rgba(107,47,160,0.45)"
            />
            {/* S1 text */}
            <text
              x="20"
              y="27"
              textAnchor="middle"
              fill="#ffffff"
              fontSize="13"
              fontWeight="700"
              fontFamily="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
              letterSpacing="-0.5"
            >
              S1
            </text>
          </svg>
        </div>
        <div className="header-titles">
          <span className="header-app-name">RulesPilot</span>
          <span className="header-tagline">AI-powered NAC Rule Creation</span>
        </div>
      </div>
    </header>
  );
}

export default Header;
