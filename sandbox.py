import queue

q = queue.PriorityQueue()

q.put((5, "stuff do do"))
q.put((1, "more stuff"))
q.put((2, "still stuff"))

print(q.get())
q.put((0, "stuff do do"))

q.put((6, "stuff do do"))

while q.qsize() > 0 :
    print(q.get()[1])
