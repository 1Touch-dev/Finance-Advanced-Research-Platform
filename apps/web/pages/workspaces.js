import { useState, useEffect } from 'react';
import Head from 'next/head';
import NoDataCard from '../src/components/NoDataCard';
import { isNoData } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function WorkspacesPage() {
  const [workspaces, setWorkspaces] = useState([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState(null);
  const [activity, setActivity] = useState([]);
  const [noData, setNoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  async function fetchWorkspaces() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/workspaces/`);
      const data = await res.json();
      if (isNoData(data)) {
        setNoData(data);
        setLoading(false);
        return;
      }
      setWorkspaces(data.workspaces || []);
      if (data.workspaces?.length > 0) {
        selectWorkspace(data.workspaces[0].workspace_id);
      }
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  async function selectWorkspace(id) {
    try {
      const [wsRes, actRes] = await Promise.all([
        fetch(`${API_BASE}/workspaces/${id}`),
        fetch(`${API_BASE}/workspaces/${id}/activity`)
      ]);
      const wsData = await wsRes.json();
      const actData = await actRes.json();
      setSelectedWorkspace(wsData);
      setActivity(actData.activity || []);
    } catch (err) {
      console.error('Error:', err);
    }
  }

  async function createWorkspace() {
    try {
      const res = await fetch(`${API_BASE}/workspaces/?name=${encodeURIComponent(newWorkspaceName)}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.workspace_id) {
        setShowCreateModal(false);
        setNewWorkspaceName('');
        fetchWorkspaces();
      }
    } catch (err) {
      console.error('Error:', err);
    }
  }

  const roleColors = {
    owner: 'bg-purple-800 text-purple-200',
    admin: 'bg-blue-800 text-blue-200',
    editor: 'bg-green-800 text-green-200',
    viewer: 'bg-gray-700 text-gray-200'
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Workspaces | Finance Platform</title>
      </Head>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Shared Workspaces</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg"
        >
          + New Workspace
        </button>
      </div>

      {noData ? (
        <NoDataCard {...noData} dataType="workspace" />
      ) : loading ? (
        <div className="text-center py-10">Loading...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Workspace List */}
          <div className="lg:col-span-1">
            <div className="bg-gray-800 rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-4">Your Workspaces</h2>
              <div className="space-y-2">
                {workspaces.map(ws => (
                  <div
                    key={ws.workspace_id}
                    onClick={() => selectWorkspace(ws.workspace_id)}
                    className={`p-3 rounded-lg cursor-pointer transition ${
                      selectedWorkspace?.workspace_id === ws.workspace_id
                        ? 'bg-blue-900 border border-blue-600'
                        : 'bg-gray-700 hover:bg-gray-650'
                    }`}
                  >
                    <div className="font-medium">{ws.name}</div>
                    <div className="text-gray-400 text-sm">{ws.member_count} members</div>
                    <span className={`inline-block mt-1 px-2 py-0.5 rounded text-xs ${roleColors[ws.user_role] || roleColors.viewer}`}>
                      {ws.user_role}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Workspace Details */}
          <div className="lg:col-span-3">
            {selectedWorkspace ? (
              <>
                {/* Header */}
                <div className="bg-gray-800 rounded-lg p-6 mb-6">
                  <h2 className="text-2xl font-bold">{selectedWorkspace.name}</h2>
                  <p className="text-gray-400 mt-1">{selectedWorkspace.description}</p>
                  <div className="flex gap-4 mt-4 text-sm text-gray-400">
                    <span>Created: {new Date(selectedWorkspace.created_at).toLocaleDateString()}</span>
                    <span>•</span>
                    <span>{selectedWorkspace.member_count} members</span>
                  </div>
                </div>

                {/* Resources */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div className="bg-gray-800 p-4 rounded-lg">
                    <h3 className="font-semibold text-gray-400 mb-2">Watchlists</h3>
                    <div className="text-2xl font-bold">{selectedWorkspace.watchlists?.length || 0}</div>
                    <div className="mt-2 space-y-1">
                      {selectedWorkspace.watchlists?.slice(0, 3).map(id => (
                        <div key={id} className="text-sm text-blue-400">{id}</div>
                      ))}
                    </div>
                  </div>
                  <div className="bg-gray-800 p-4 rounded-lg">
                    <h3 className="font-semibold text-gray-400 mb-2">Dashboards</h3>
                    <div className="text-2xl font-bold">{selectedWorkspace.dashboards?.length || 0}</div>
                    <div className="mt-2 space-y-1">
                      {selectedWorkspace.dashboards?.slice(0, 3).map(id => (
                        <div key={id} className="text-sm text-blue-400">{id}</div>
                      ))}
                    </div>
                  </div>
                  <div className="bg-gray-800 p-4 rounded-lg">
                    <h3 className="font-semibold text-gray-400 mb-2">Reports</h3>
                    <div className="text-2xl font-bold">{selectedWorkspace.reports?.length || 0}</div>
                    <div className="mt-2 space-y-1">
                      {selectedWorkspace.reports?.slice(0, 3).map(id => (
                        <div key={id} className="text-sm text-blue-400">{id}</div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Members */}
                <div className="bg-gray-800 rounded-lg p-4 mb-6">
                  <h3 className="text-lg font-semibold mb-4">Members</h3>
                  <div className="space-y-2">
                    {selectedWorkspace.members?.map(member => (
                      <div key={member.user_id} className="flex items-center justify-between p-3 bg-gray-700 rounded-lg">
                        <div>
                          <div className="font-medium">{member.name}</div>
                          <div className="text-gray-400 text-sm">{member.email}</div>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs ${roleColors[member.role]}`}>
                          {member.role}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Activity */}
                <div className="bg-gray-800 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
                  <div className="space-y-3">
                    {activity.map((act, i) => (
                      <div key={i} className="flex items-start gap-3 text-sm">
                        <div className="text-gray-500 whitespace-nowrap">
                          {new Date(act.timestamp).toLocaleDateString()}
                        </div>
                        <div>
                          <span className="text-blue-400">{act.user}</span>{' '}
                          <span className="text-gray-400">{act.type.replace('_', ' ')}</span>
                          {act.resource && <span className="text-white"> {act.resource}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center text-gray-400 py-10">
                Select a workspace to view details
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
          <div className="bg-gray-800 p-6 rounded-lg w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Create New Workspace</h2>
            <input
              type="text"
              value={newWorkspaceName}
              onChange={(e) => setNewWorkspaceName(e.target.value)}
              placeholder="Workspace name"
              className="w-full bg-gray-700 border border-gray-600 rounded px-4 py-2 mb-4"
            />
            <div className="flex gap-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded"
              >
                Cancel
              </button>
              <button
                onClick={createWorkspace}
                className="flex-1 bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
