import{ useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

const TopologyView = () => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/topology')
      .then(res => res.json())
      .then(data => {
        // Format for the graph library
        setGraphData({
          nodes: data.nodes.map((n: any) => ({ id: n.id, name: n.id })),
          links: data.edges.map((e: any) => ({ source: e.source, target: e.target }))
        });
        setIsLoading(false);
      })
      .catch(err => {
        console.error("Error loading topology:", err);
        setIsLoading(false);
      });
  }, []);

  return (
    <div className="h-full w-full bg-slate-900 rounded-xl overflow-hidden border border-slate-700/50 flex flex-col items-center justify-center">
      {isLoading ? (
        <div className="text-cyan-400 font-mono animate-pulse">Mapping Network...</div>
      ) : graphData.nodes.length > 0 ? (
        <ForceGraph2D
          graphData={graphData}
          nodeLabel="id"
          nodeAutoColorBy="id"
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          linkColor={() => '#475569'}
          width={800} // You can adjust this to fit your dashboard width later
          height={600}
        />
      ) : (
        <div className="text-slate-400 font-mono">No topology data found.</div>
      )}
    </div>
  );
};

export default TopologyView;