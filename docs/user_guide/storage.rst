Data Storage
============

MatSimPy provides persistent storage for structures and calculation results.
Storage uses the optional ``maggma`` dependency; install it with
``pip install MatSimPy[storage]`` before constructing ``DataStorage``.

For complete API documentation, see :doc:`../api_reference/storage`.

Usage Examples
--------------

.. code-block:: python

   from matsimpy.storage import DataStorage
   from matsimpy.builders.bulk import from_prototype

   # Initialize storage
   storage = DataStorage(store_path="materials_simulation_data.json")

   # Store crystal structure
   crystal = from_prototype('diamond', 'Si', 5.43)
   doc_id = storage.store_data(crystal, metadata={'description': 'Si primitive cell'})

   # Store calculation results
   results = {'energy': -10.5, 'forces': [[0,0,0]]}
   storage.store_data(results, metadata={'calculator': 'LJ'})

   # Retrieve and query
   retrieved = storage.retrieve_data(doc_id)
   lj_results = storage.retrieve_data(query={'metadata.calculator': 'LJ'})

   storage.close()
