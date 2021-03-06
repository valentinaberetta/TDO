import os

class Graph():
    ''' Oriented Graph'''
    nodes = None # set of nodes ids
    adjacents = None # map< key: node id, value: set of adjacent node ids >

    def __init__(self):
        self.nodes = set();
        self.adjacents = dict()

    def addNode(self, node):
        if not node in self.nodes: self.nodes.add(node)

    def addNodes(self, nodes):
        for n in nodes: self.addNode(n)

    def addLink(self, source, target):
        if not source in self.adjacents: self.adjacents[source] = set()
        if not target in self.adjacents.get(source):
            self.adjacents.get(source).add(target)
        if not source in self.nodes: self.nodes.add(source)
        if not target in self.nodes: self.nodes.add(target)

    def __str__(self):
        out = "-----------------------------------------------------------------\n"
        out += "Graph: "+str(len(self.nodes))+"\n"
        out += "-----------------------------------------------------------------\n"
        return out

'''
Flush the specified graph into a file respecting the following format
adjancency list, one entry per line, e.g.
node_id[\t]node_id_O;node_id_1;...

g: graph stored into adjacency lists using a dictionary key node value iterable collection of adjacent nodes
file_: file path
'''
def flushGraph(g, file_):
    f = open(file_,'w', encoding='utf-8')
    for k in g.nodes:
        s = ""
        if not k in g.adjacents: s = "none"
        else:
            for v in g.adjacents.get(k):
                if(len(s)!=0):
                    s += ";"
                s += v
        f.write(k+"\t"+s+'\n') # python will convert \n to os.linesep
    f.close()

def loadGraphOfURIs(file_, header):
    print ("Loading the graph from: ",file_)
    g = Graph()

    with open(file_, "r", encoding='utf-8') as reader:

        for line in reader:

            if header:
                header = False
                continue

            line = line.strip()

            data = line.split("\t")
            uri_c = data[0]

            if len(data)!=2:
                print ("[warning] excluding line ", line)
                continue
            if(data[1] == "none"):
                g.addNode(uri_c[0])
                continue

            ancestors = data[1].split(";http")

            for a in range(0,len(ancestors)):

                uri_a = ancestors[a]
                if(a != 0): uri_a = "http"+uri_a
                g.addLink(uri_c,uri_a)

    print (g.__str__())
    return g

def compute_exclusive_descendants(g):
	d = {}
	for node in g.nodes:
		d[node] = 0
		if (g.adjacents.get(node)!=None):
			for a in g.adjacents.get(node):
				if(a == node): continue
				if not a in d: d[a] = 1
				else: d[a] += 1
		else:
			print("Node" + str(node))
	return d

def perform_transitive_reduction(g):

	nb_descendants = compute_exclusive_descendants(g)
	# detects the leaves
	leaves = set()
	for d in nb_descendants:
		if(nb_descendants[d] == 0): leaves.add(d)

	print ("Number of detected leaves", str(len(leaves)))

	queue = list(leaves)

	desc = {}
	rel_removed = 0

	j = 0

	g_reduced = Graph()
	g_reduced.addNodes(g.nodes)

	while queue:

		j+=1

		if j % 10000 == 0:
			print (str(j)+"/"+str(len(g.nodes)))

		c = queue.pop(0)

		if not c in desc: desc[c] = set()

		desc[c].add(c)

		if not c in g.adjacents: continue # no ancestors for that value

		# propagation of the descendants of c to it's ancestors
		for a in g.adjacents.get(c):

			if(a == c):
				continue # we don't want to add c -> a and the number of descendants is already exclusive

			g_reduced.addLink(c,a)

			todel = set()
			if not a in desc: desc[a] = set()

			# propagation
			for d in desc[c]:

				if (d in desc[a]) or (d == a): # the relationship can be removed
					todel.add(d) # d -> a can be removed since we have d -> ... -> c -> a
				else:
					desc[a].add(d)

			# reduce the graph considering detected redundancies
			for d in todel:
				if a in g.adjacents.get(d): # the error is maybe already corrected
					g.adjacents.get(d).remove(a)
					rel_removed += 1

			nb_descendants[a] -= 1

			# now we can propagate the descendants of this node
			# since we are sure all the descendants have been propagated
			if(nb_descendants[a] == 0): queue.append(a)

	print ("Number of relations removed ", str(rel_removed))

	return g_reduced

def load_graph(graph_file, graph_file_reduced, apply_transitive_reduction):
	print("loading graph")
	if apply_transitive_reduction:
		g = loadGraphOfURIs(graph_file, True)
		print ("performing the transitive reduction (to avoid useless propagations)")
		g = perform_transitive_reduction(g)

		print ("Flushing reduction into: ",graph_file_reduced)
		flushGraph(g,graph_file_reduced)

	else:
		g = loadGraphOfURIs(graph_file_reduced, False)
	return g

def load_nb_descendants_d(g, value_sources):
	nb_descendants_d ={}

	queue_p = list(value_sources.keys())
	visited = set(queue_p)

	while(queue_p):

		c = queue_p.pop(0)
		visited.add(c)
		if(not c in nb_descendants_d): nb_descendants_d[c] = 0

		if not c in g.adjacents: continue

		for a in g.adjacents.get(c):

			if not a in visited:
				queue_p.append(a)
				visited.add(a)

			if not a in nb_descendants_d:
				nb_descendants_d[a] = 1
			else:
				nb_descendants_d[a] += 1

	return  nb_descendants_d

def create_value_info_computation(g, sources_dataItemValues, D, dataitem_index_file, confidence_value_computation_info_dir):
	#in source dataitemValues the dataitem are present in form of ID
	print ("Results will be stored into: ", confidence_value_computation_info_dir)
	if not os.path.exists(confidence_value_computation_info_dir):
		os.makedirs(confidence_value_computation_info_dir)
	d_cont = 0
	dataItemIds = {} # dataitems will be indexed to generate file names

	for d in sources_dataItemValues:
		d_cont += 1
		print (str(d_cont),"/",str(len(sources_dataItemValues)))

		# sources for each value
		d_value_sources = sources_dataItemValues[d]

		print ("computing reduction")
		# Now we compute the number of descendants of each nodes
		# which require to be considered in order to be able to apply the BFS
		# for propagating sources
		# Remember that a transitive reduction has been applied

		nb_descendants_d = load_nb_descendants_d(g, d_value_sources)

		# if you need the subgraph considered you just have to load
		# the adjacency lists of the graph (with transitive reduction)
		# for the visited values - these values will be stored in the result file
		# generated below

		# Propagation will start for the leaves of the redution
		queue_tmp = list()

		for c in nb_descendants_d.keys():
			if nb_descendants_d[c] == 0: queue_tmp.append(c)

		print ("initial queue contains ", len(queue_tmp),"/",len(nb_descendants_d.keys()),"/",len(g.nodes)," values")


		value_confidence_to_sum = {}
		new_sources = {}
		source_trustwordiness_to_remove = {}
		source_trustwordiness_to_add = {}

		visited = list()

		while (queue_tmp):

			n = queue_tmp.pop(0)

			if not n in new_sources: new_sources[n] = set()
			if not n in d_value_sources: d_value_sources[n] = set()

			source_trustwordiness_to_add[n] = d_value_sources[n].difference(new_sources[n])
			new_sources[n] = new_sources[n] | d_value_sources[n]

			visited.append(n)

			if not n in g.adjacents: continue

			for a in g.adjacents.get(n):
				if not a in new_sources: new_sources[a] = set()
				if not a in source_trustwordiness_to_remove: source_trustwordiness_to_remove[a] = {}

				for t in new_sources[a].intersection(d_value_sources[n]):
					if not t in source_trustwordiness_to_remove[a]:
						source_trustwordiness_to_remove[a][t] = 1
					else:
						source_trustwordiness_to_remove[a][t] += 1

				new_sources[a] = new_sources[a] | new_sources[n]

				nb_descendants_d[a] -= 1
				if nb_descendants_d[a] == 0: queue_tmp.append(a)

				if not a in value_confidence_to_sum:
					value_confidence_to_sum[a] = set()

				value_confidence_to_sum[a].add(n)

		# just to check - this is for debugging
		# it can be removed after careful proof-reading
		for  c in nb_descendants_d:
			if nb_descendants_d[c] != 0:
				print ("Error detected... refer to devs")
				quit()


		print ("Flushing results into: "+confidence_value_computation_info_dir+"/"+str(d_cont)+".csv")
		f = open(confidence_value_computation_info_dir+"/"+str(d_cont)+".csv",'w', encoding='utf-8')

		stop = False

		for n in visited:

			n_value_confidence_to_sum = "none"
			n_source_trustwordiness_to_add = "none"
			n_source_trustwordiness_to_remove = "none"

			if n in value_confidence_to_sum and len(value_confidence_to_sum[n]) != 0:
				n_value_confidence_to_sum = ""
				for v in value_confidence_to_sum[n]:
					if(len(n_value_confidence_to_sum)!=0):
						n_value_confidence_to_sum += "-----"
					n_value_confidence_to_sum += v

			if n in source_trustwordiness_to_add and len(source_trustwordiness_to_add[n]) != 0:
				n_source_trustwordiness_to_add = ""
				for v in source_trustwordiness_to_add[n]:
					if(len(n_source_trustwordiness_to_add)!=0):
						n_source_trustwordiness_to_add += ";"
					n_source_trustwordiness_to_add += str(v)

			if n in source_trustwordiness_to_remove and len(source_trustwordiness_to_remove[n]) != 0 :

				n_source_trustwordiness_to_remove = ""

				for v in source_trustwordiness_to_remove[n]:
					if(len(n_source_trustwordiness_to_remove)!=0):
						n_source_trustwordiness_to_remove += ";"
					n_source_trustwordiness_to_remove += v+"="+str(source_trustwordiness_to_remove[n][v])

				print ("Things to remove to compute ", n)
				stop = True

			source_string_propagated = ""
			for ns in new_sources[n]:
				if(len(source_string_propagated)!=0): source_string_propagated += ";"
				source_string_propagated += str(ns)

			f.write(n+"\t"+n_value_confidence_to_sum+"\t"+n_source_trustwordiness_to_add+"\t"+n_source_trustwordiness_to_remove+"\t"+source_string_propagated+'\n')

		f.close()
		if(stop): exit()

		dataItemIds[d] = d_cont # stores the id of the value

	print ("flushing dataitem index into: "+dataitem_index_file)
	# Write dataitem index
	f = open(dataitem_index_file,'w', encoding='utf-8')
	for k in dataItemIds:
		f.write(k+"\t"+str(dataItemIds[k])+'\n')
	f.close()

