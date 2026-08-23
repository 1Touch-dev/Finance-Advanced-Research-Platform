import { useState, useEffect } from 'react';
import Head from 'next/head';
import NoDataCard from '../src/components/NoDataCard';
import { isNoData , apiFetch } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function TeamsPage() {
  const [teams, setTeams] = useState([]);
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [memberPermissions, setMemberPermissions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [noData, setNoData] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    setLoading(true);
    try {
      const [teamsRes, rolesRes, permsRes] = await Promise.all([
        apiFetch(`/teams/`),
        apiFetch(`/teams/roles`),
        apiFetch(`/teams/permissions`)
      ]);
      const teamsData = await teamsRes.json();
      if (isNoData(teamsData)) { setNoData(teamsData); setLoading(false); return; }
      const rolesData = await rolesRes.json();
      const permsData = await permsRes.json();
      setTeams(teamsData.teams || []);
      setRoles(rolesData.roles || []);
      setPermissions(permsData.permissions || []);
      if (teamsData.teams?.length > 0) {
        selectTeam(teamsData.teams[0].team_id);
      }
    } catch (err) {
      console.error('Error:', err);
    }
    setLoading(false);
  }

  async function selectTeam(id) {
    try {
      const res = await apiFetch(`/teams/${id}`);
      const data = await res.json();
      setSelectedTeam(data);
    } catch (err) {
      console.error('Error:', err);
    }
  }

  async function viewMemberPerms(userId) {
    try {
      const res = await apiFetch(`/teams/${selectedTeam.team_id}/members/${userId}/permissions`);
      const data = await res.json();
      setMemberPermissions({ userId, ...data });
    } catch (err) {
      console.error('Error:', err);
    }
  }

  const roleColors = {
    owner: 'bg-purple-600',
    admin: 'bg-blue-600',
    editor: 'bg-green-600',
    viewer: 'bg-gray-600'
  };

  const categoryColors = {
    read: 'text-green-400',
    write: 'text-blue-400',
    admin: 'text-purple-400',
    other: 'text-gray-400'
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Head>
        <title>Team Permissions | Finance Platform</title>
      </Head>

      <h1 className="text-3xl font-bold mb-6">Team Permission Roles</h1>

      {loading ? (
        <div className="text-center py-10">Loading...</div>
      ) : noData ? (
        <NoDataCard {...noData} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Roles Reference */}
          <div className="lg:col-span-1">
            <div className="bg-gray-800 rounded-lg p-4 mb-6">
              <h2 className="text-lg font-semibold mb-4">Available Roles</h2>
              <div className="space-y-3">
                {roles.map(role => (
                  <div key={role.role} className="p-3 bg-gray-700 rounded-lg">
                    <div className="flex items-center gap-2">
                      <span className={`w-3 h-3 rounded-full ${roleColors[role.role]}`}></span>
                      <span className="font-semibold capitalize">{role.role}</span>
                      <span className="text-gray-400 text-sm">({role.permission_count} perms)</span>
                    </div>
                    <p className="text-gray-400 text-sm mt-1">{role.description}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* All Permissions */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-4">All Permissions</h2>
              <div className="space-y-1 text-sm">
                {permissions.map(perm => (
                  <div key={perm.permission} className="flex items-center gap-2">
                    <span className={categoryColors[perm.category]}>●</span>
                    <span>{perm.permission.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Team Details */}
          <div className="lg:col-span-2">
            {/* Team Selector */}
            <div className="flex gap-2 mb-6">
              {teams.map(team => (
                <button
                  key={team.team_id}
                  onClick={() => selectTeam(team.team_id)}
                  className={`px-4 py-2 rounded-lg ${
                    selectedTeam?.team_id === team.team_id
                      ? 'bg-blue-600'
                      : 'bg-gray-700 hover:bg-gray-600'
                  }`}
                >
                  {team.name}
                </button>
              ))}
            </div>

            {selectedTeam && (
              <>
                {/* Team Info */}
                <div className="bg-gray-800 rounded-lg p-6 mb-6">
                  <h2 className="text-2xl font-bold">{selectedTeam.name}</h2>
                  <div className="flex gap-4 mt-2 text-gray-400 text-sm">
                    <span>Owner: {selectedTeam.owner_id}</span>
                    <span>•</span>
                    <span>{selectedTeam.member_count} members</span>
                  </div>
                </div>

                {/* Members */}
                <div className="bg-gray-800 rounded-lg p-4 mb-6">
                  <h3 className="text-lg font-semibold mb-4">Team Members</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-700">
                        <tr>
                          <th className="px-4 py-2 text-left">Name</th>
                          <th className="px-4 py-2 text-left">Email</th>
                          <th className="px-4 py-2 text-center">Role</th>
                          <th className="px-4 py-2 text-center">Permissions</th>
                          <th className="px-4 py-2 text-center">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedTeam.members?.map(member => (
                          <tr key={member.user_id} className="border-t border-gray-700">
                            <td className="px-4 py-3 font-medium">{member.name}</td>
                            <td className="px-4 py-3 text-gray-400">{member.email}</td>
                            <td className="px-4 py-3 text-center">
                              <span className={`px-2 py-1 rounded text-xs ${roleColors[member.role]} text-white`}>
                                {member.role}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-center text-gray-400">
                              {member.permissions?.length || 0}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <button
                                onClick={() => viewMemberPerms(member.user_id)}
                                className="text-blue-400 hover:text-blue-300 text-sm"
                              >
                                View Perms
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Member Permissions Detail */}
                {memberPermissions && (
                  <div className="bg-gray-800 rounded-lg p-4">
                    <h3 className="text-lg font-semibold mb-4">
                      Permissions for {memberPermissions.userId}
                      <span className={`ml-2 px-2 py-1 rounded text-xs ${roleColors[memberPermissions.role]} text-white`}>
                        {memberPermissions.role}
                      </span>
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {memberPermissions.permissions?.map(perm => (
                        <div key={perm} className="flex items-center gap-2 text-sm">
                          <span className="text-green-400">✓</span>
                          <span>{perm.replace(/_/g, ' ')}</span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 pt-4 border-t border-gray-700 flex gap-4 text-sm">
                      <span className={memberPermissions.can_edit ? 'text-green-400' : 'text-red-400'}>
                        {memberPermissions.can_edit ? '✓' : '✗'} Can Edit
                      </span>
                      <span className={memberPermissions.can_manage ? 'text-green-400' : 'text-red-400'}>
                        {memberPermissions.can_manage ? '✓' : '✗'} Can Manage
                      </span>
                      <span className={memberPermissions.is_admin ? 'text-green-400' : 'text-red-400'}>
                        {memberPermissions.is_admin ? '✓' : '✗'} Is Admin
                      </span>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
