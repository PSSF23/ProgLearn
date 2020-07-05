import numpy as np


class ProgressiveLearner:
    def __init__(self, default_transformer_class = None, default_transformer_kwargs = None,
        default_voter_class = None, default_voter_kwargs = None,
        default_decider_class = None, default_decider_kwargs = None
    ):
        
        self.task_id_to_X = {}
        self.task_id_to_y = {}

        self.transformer_id_to_transformers = {} # transformer id to a fitted transformers
        self.task_id_to_transformer_id_to_voters = {} # task id to a map from transformer ids to a fitted voter
        self.task_id_to_decider = {} # task id to a fitted decider 
        
        self.transformer_id_to_voter_class = {} # might be expensive to keep around and hints at need for default voters
        self.transformer_id_to_voter_kwargs = {}

        self.task_id_to_decider_class = {} # task id to uninstantiated decider class
        self.task_id_to_decider_kwargs = {} # task id to decider kwargs 

        self.default_transformer_class = default_transformer_class
        self.default_transformer_kwargs = default_transformer_kwargs

        self.default_voter_class = default_voter_class
        self.default_voter_kwargs = default_voter_kwargs

        self.default_decider_class = default_decider_class
        self.default_decider_kwargs = default_decider_kwargs
        
    def get_transformer_ids(self):
        return np.array(list(self.transformer_id_to_transformers.keys()))

    def get_task_ids(self):
        return np.array(list(self.task_id_to_decider.keys()))
    
    def _append_transformer(self, transformer_id, transformer):
        if transformer_id in self.get_transformer_ids():
            self.transformer_id_to_transformers[transformer_id].append(transformer)
        else:
            self.transformer_id_to_transformers[transformer_id] = [transformer]
            
    def _append_voter(self, transformer_id, task_id, voter):
        if task_id in list(self.task_id_to_transformer_id_to_voters.keys()):
            if transformer_id in list(self.task_id_to_transformer_id_to_voters[task_id].keys()):
                self.task_id_to_transformer_id_to_voters[task_id][transformer_id].append(voter)
            else:
                self.task_id_to_transformer_id_to_voters[task_id][transformer_id] = [voter]
        else:
            self.task_id_to_transformer_id_to_voters[task_id] = {transformer_id : [voter]}
            
    def _get_transformer_voter_decider_idx(self, n, transformer_voter_decider_split):
        if transformer_voter_decider_split is None:
            transformer_idx, voter_idx, decider_idx = np.arange(n), np.arange(n), np.arange(n)
        elif np.sum(transformer_voter_decider_split) > 1:
            transformer_idx, voter_idx, decider_idx = [np.random.choice(np.arange(n), int(n*split)) for split in transformer_voter_decider_split]
        else:
            transformer_idx = np.random.choice(
                np.arange(n), 
                int(n*transformer_voter_decider_split[0])
            )

            voter_idx = np.random.choice(
                np.delete(np.arange(n), transformer_idx), 
                int(n*transformer_voter_decider_split[1])
            )

            decider_idx = np.random.choice(
                np.delete(np.arange(n), np.concatenate((transformer_idx, voter_idx))),
                int(n*transformer_voter_decider_split[2])
            )
        return transformer_idx, voter_idx, decider_idx

    def set_transformer(self, X=None, y=None, transformer_id=None, transformer_class=None, transformer_kwargs=None, default_voter_class = None, default_voter_kwargs = None,
        transformer = None):

        if transformer_id is None:
            transformer_id = len(self.get_transformer_ids())

        if X is None and y is None:
            if transformer.is_fitted():
                self._append_transformer(transformer_id, transformer)
            else:
                raise ValueError('transformer_class is not fitted and X is None and y is None.')
            return 

        # Type check X

        if transformer_class is None:
            if self.default_transformer_class is None:
                raise ValueError("transformer_class is None and 'default_transformer_class' is None.")
            else:
                transformer_class = self.default_transformer_class
                
        if transformer_kwargs is None:
            if self.default_transformer_kwargs is None:
                raise ValueError("transformer_kwargs is None and 'default_transformer_kwargs' is None.")
            else:
                transformer_kwargs = self.default_transformer_kwargs

        # Fit transformer and new voter
        if y is None:
            self._append_transformer(transformer_id, transformer_class(**transformer_kwargs).fit(X))
        else:
            # Type check y
            self._append_transformer(transformer_id, transformer_class(**transformer_kwargs).fit(X, y))
            
        self.transformer_id_to_voter_class[transformer_id] = default_voter_class
        self.transformer_id_to_voter_kwargs[transformer_id] = default_voter_kwargs

    def set_voter(self, X, y, transformer_id, task_id = None,
         voter_class = None, voter_kwargs = None, bag_id = None):

        # Type check X

        # Type check y
        
        if task_id is None:
            task_id = len(self.get_task_ids())
            
        if voter_class is None:
            if self.transformer_id_to_voter_class[transformer_id] is not None:
                voter_class = self.transformer_id_to_voter_class[transformer_id]
            elif self.default_voter_class is not None:
                voter_class = self.default_voter_class
            else:
                raise ValueError("voter_class is None, the default voter class for the overall learner is None, and the default voter class for this transformer is None.")

        if voter_kwargs is None:
            if self.transformer_id_to_voter_kwargs[transformer_id] is not None:
                voter_kwargs = self.transformer_id_to_voter_kwargs[transformer_id]
            elif self.default_voter_kwargs is not None:
                voter_kwargs = self.default_voter_kwargs
            else:
                raise ValueError("voter_kwargs is None, the default voter kwargs for the overall learner is None, and the default voter kwargs for this transformer is None.")
        
        if bag_id == None:
            transformers = self.transformer_id_to_transformers[transformer_id]
        else:
            transformers = [self.transformer_id_to_transformers[transformer_id][bag_id]]
        for _, transformer in enumerate(transformers):
            self._append_voter(transformer_id, task_id, voter_class(**voter_kwargs).fit(transformer.transform(X), y))

    def set_decider(self, task_id, transformer_ids, X = None, y = None,
        decider_class=None, decider_kwargs=None):

        if decider_class is None:
            if self.default_decider_class is None:
                raise ValueError("decider_class is None and 'default_decider_class' is None.")
            else:
                decider_class = self.default_decider_class

        if decider_kwargs is None:
            if self.default_decider_kwargs is None:
                raise ValueError("decider_kwargs is None and 'default_decider_kwargs' is None.")
            else:
                decider_kwargs = self.default_decider_kwargs
                
        transformer_id_to_transformers = {transformer_id : self.transformer_id_to_transformers[transformer_id] for transformer_id in transformer_ids}
        transformer_id_to_voters = {transformer_id : self.task_id_to_transformer_id_to_voters[task_id][transformer_id] for transformer_id in transformer_ids}
        
        self.task_id_to_decider[task_id] = decider_class(**decider_kwargs).fit(transformer_id_to_transformers = transformer_id_to_transformers, 
                                                                               transformer_id_to_voters = transformer_id_to_voters, 
                                                                               X=X, 
                                                                               y=y)
        
        self.task_id_to_decider_class[task_id] = decider_class
        self.task_id_to_decider_kwargs[task_id] = decider_kwargs
        
    def add_task(self, X, y, 
                 task_id=None, transformer_voter_decider_split = None, num_transformers = 1,
                 transformer_class=None, transformer_kwargs=None, 
                 voter_class=None, voter_kwargs=None, 
                 decider_class=None, decider_kwargs=None,
                 backward_task_ids = None, forward_transformer_ids = None):
        # Type check X

        # Type check y
        
        if task_id is None:
            task_id = max(len(self.get_transformer_ids()), len(self.get_task_ids())) #come up with something that has fewer collisions
            
        self.task_id_to_X[task_id] = X
        self.task_id_to_y[task_id] = y

        if transformer_class is None and num_transformers > 1:
            if self.default_transformer_class is None:
                raise ValueError("transformer_class is None and 'default_transformer_class' is None.")
            else:
                transformer_class = self.default_transformer_class

        if voter_class is None:
            if self.default_voter_class is None:
                raise ValueError("voter_class is None and 'default_voter_class' is None.")
            else:
                voter_class = self.default_voter_class

        if decider_class is None:
            if self.default_decider_class is None:
                raise ValueError("decider_class is None and 'default_decider_class' is None.")
            else:
                decider_class = self.default_decider_class
                
        if transformer_kwargs is None and num_transformers > 1:
            if self.default_transformer_kwargs is None:
                raise ValueError("transformer_kwargs is None and 'default_transformer_kwargs' is None.")
            else:
                transformer_kwargs = self.default_transformer_kwargs

        if voter_kwargs is None:
            if self.default_voter_kwargs is None:
                raise ValueError("voter_kwargs is None and 'default_voter_kwargs' is None.")
            else:
                voter_kwargs = self.default_voter_kwargs

        if decider_kwargs is None:
            if self.default_decider_kwargs is None:
                raise ValueError("decider_kwargs is None and 'default_decider_kwargs' is None.")
            else:
                decider_kwargs = self.default_decider_kwargs
        
        for transformer_num in range(num_transformers):
            transformer_idx, voter_idx, decider_idx = self._get_transformer_voter_decider_idx(len(X), transformer_voter_decider_split)
                
            self.set_transformer(X[transformer_idx], y[transformer_idx], task_id, transformer_class, transformer_kwargs, voter_class, voter_kwargs)
        
            # train voters from previous tasks to new task
            for transformer_id in forward_transformer_ids if forward_transformer_ids else self.get_transformer_ids():
                if transformer_id == task_id:
                    self.set_voter(X[voter_idx], y[voter_idx], transformer_id, task_id, voter_class, voter_kwargs, bag_id = transformer_num)
                else:
                    self.set_voter(X, y, transformer_id, task_id, bag_id = transformer_num)
                    
            if transformer_num == num_transformers - 1:
                self.set_decider(task_id = task_id, 
                                 transformer_ids = self.get_transformer_ids(), 
                                 X = X[decider_idx], 
                                 y = y[decider_idx],
                                 decider_class = decider_class, 
                                 decider_kwargs = decider_kwargs)

            # train voters from new transformer to previous tasks
            if num_transformers > 0:
                for existing_task_id in backward_task_ids if backward_task_ids else self.get_task_ids():
                    if existing_task_id == task_id:
                        continue
                    else:
                        existing_X = self.task_id_to_X[existing_task_id]
                        existing_y = self.task_id_to_y[existing_task_id]
                        self.set_voter(X = existing_X, 
                                       y = existing_y, 
                                       transformer_id = task_id, 
                                       task_id = existing_task_id,
                                       bag_id = transformer_num)
                        if transformer_num == num_transformers - 1:
                            self.set_decider(existing_task_id, self.get_transformer_ids(), X = existing_X, y = existing_y)

        
    def predict(self, X, task_id, transformer_ids = None):
        return self.task_id_to_decider[task_id].predict(X, transformer_ids = transformer_ids)