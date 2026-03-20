# Experiment Plan

### Problem Statement

For our purposes, we will likely want to evaluate a lot across the different evaluation strategies, however Sonnet 4 is a realitively expensive model. I would like to test to see if other cheaper models would provide similar results for Sonnet 4. For our final results/eval we would likely use sonnet 4 still, but in intermediate analysis we can utilize the cheaper model. 



### Methedology



The methedology of the paper is in section 2.1 and Appendix B. (https://arxiv.org/pdf/2603.10011)
In the `eval.ipynb` notebook is a notebook that attempted to evaluate the model using a replication of the 2 turn impossible numeric and impossible fraction problem framework, with similar emotion prompt as well. 


What we will need to do is utilize that, as well as the eval.py file, to build a new jupyter notebook that will run an experiment for a set number of samples, with each sample being the same question across models. 


This experiment can be a 2 turn refusal, 3 turn refusal, or a range of multiple terms. 
The end result should be a set of the same experiment, where the only difference and variation we analyze is a change in the grader-model. 


My suggested approach to this would be:


1. First read through the methedology in the paper

2. Look through the eval.ipynb notebook and get it to run locally, and possibly Arenas inspect exercise set (https://learn.arena.education/chapter3_llm_evals/03_running_evals/intro)

3. Create a notebook that will do the evaluation you want for a small sample first, like 5 samples per grader model, and evaluate the inital results to ensure no error

4. With the smaller evaluations, create visualizations that will provide you with an understanding of what to do

5. Run with larger samples once you ensure experimental design is correct, ideally through a notebook and not eval.py so that you understand what is going on better

6. Analyze the results and figures generated, and consider next experiments to run


Consider git commiting everytime before running large evals for notebooks since I think inspect eval will log commits. 


### Outputs

In this folder, put the logs utilized in the experiment, visualizations, and notebook used to do the experiment. 