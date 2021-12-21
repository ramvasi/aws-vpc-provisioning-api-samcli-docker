FROM public.ecr.aws/lambda/nodejs:14
RUN yum update -y
RUN node --version

FROM public.ecr.aws/lambda/python:3.8
RUN yum update -y

# Copy lambda function code
RUN mkdir ${LAMBDA_TASK_ROOT}/vpcx_core_infra
COPY ./ ${LAMBDA_TASK_ROOT}/vpcx_core_infra/

# Copy node runtime from previous stage
COPY --from=0 /var/lang/bin/node /bin/node

# Install the function's dependencies
COPY requirements.txt  .
RUN  pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Set the CMD to handler
CMD ["vpcx_core_infra/index.create_handler"]