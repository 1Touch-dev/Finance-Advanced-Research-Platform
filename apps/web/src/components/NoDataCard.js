import { useState } from 'react';

const REASON_EXPLANATIONS = {
  api_unavailable: 'The external data source API is temporarily unreachable or experiencing downtime.',
  dependency_missing: 'A required integration or package hasn\'t been configured yet for this environment.',
  credentials_missing: 'API credentials for the data provider haven\'t been added to the environment.',
  rate_limited: 'We\'ve hit the rate limit for this data source. Data will refresh automatically.',
  subscription_required: 'This data source requires a paid subscription that isn\'t currently active.',
  maintenance: 'The data provider is undergoing scheduled maintenance.',
  not_configured: 'This feature requires additional setup before it can display data.',
};

const DATA_TYPE_LABELS = {
  whale_flow: 'Whale Flow Data',
  reddit_sentiment: 'Reddit Sentiment',
  brokerage_sync: 'Brokerage Sync',
  benchmark: 'Benchmark Data',
  workspace: 'Workspace Data',
  narrative_model: 'Narrative Model',
  portfolio: 'Portfolio Data',
  earnings: 'Earnings Data',
};

export default function NoDataCard({ reason, message, details, source, data_type, dataType }) {
  const [expanded, setExpanded] = useState(false);
  const type = data_type || dataType;

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-2xl mx-auto">
      <div className="flex items-start gap-4">
        <div className="text-3xl flex-shrink-0 mt-1" aria-hidden="true">
          &#x1F4CB;
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {type && (
              <span className="px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded font-medium uppercase tracking-wide">
                {DATA_TYPE_LABELS[type] || type.replace(/_/g, ' ')}
              </span>
            )}
            {source && (
              <span className="px-2 py-0.5 bg-gray-700 text-gray-400 text-xs rounded">
                {source}
              </span>
            )}
          </div>

          <p className="text-gray-200 text-lg font-medium mt-3">
            {message || 'Data is not available at this time'}
          </p>

          {details && (
            <p className="text-gray-400 text-sm mt-2">
              {details}
            </p>
          )}

          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-4 text-sm text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1"
          >
            <span>{expanded ? '▾' : '▸'}</span>
            <span>Why is this happening?</span>
          </button>

          {expanded && (
            <div className="mt-3 p-4 bg-gray-900 rounded-lg text-sm text-gray-400 space-y-2">
              {reason && REASON_EXPLANATIONS[reason] && (
                <p>{REASON_EXPLANATIONS[reason]}</p>
              )}
              <p className="text-gray-500">
                This is expected for features that require external data sources or integrations
                not yet configured in the current environment. No action is needed unless
                you expect this data to be available.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
